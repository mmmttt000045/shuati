"""
数据加载器模块 - 专门处理题目数据的加载和同步
"""
import glob
import logging
import os
from typing import List, Dict, Any, Union
import pandas as pd

from .config import SUBJECT_DIRECTORY, SHEET_NAME, QUESTION_COLUMN, ANSWER_COLUMN
from .utils import standardize_tf_answer, is_tf_answer, normalize_filepath, get_file_hash
from .connectDB import (
    get_all_questions_by_tiku_dict, get_all_subjects, create_subject,
    create_or_update_tiku, delete_questions_by_tiku, parse_excel_to_questions,
    insert_questions_batch
)

logger = logging.getLogger(__name__)


def load_questions_from_excel(filepath: str, sheetname: Union[str, int]) -> List[Dict[str, Any]]:
    """从Excel文件加载题目"""
    if not os.path.exists(filepath):
        logger.error(f"Question bank file '{filepath}' not found.")
        return None

    try:
        df = pd.read_excel(filepath, sheet_name=sheetname, dtype=str)
        df.columns = [col.strip() for col in df.columns]

        required_cols = [QUESTION_COLUMN, ANSWER_COLUMN]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns in '{filepath}': {', '.join(missing_cols)}")
            return []

        questions_data = []
        for index, row in df.iterrows():
            try:
                question_text = str(row.get(QUESTION_COLUMN, '')).strip()
                raw_answer_text = str(row.get(ANSWER_COLUMN, '')).strip()

                if not question_text or not raw_answer_text or question_text.lower() == 'nan' or raw_answer_text.lower() == 'nan':
                    continue

                # 处理判断题
                if is_tf_answer(raw_answer_text):
                    processed_answer = standardize_tf_answer(raw_answer_text)
                    if not processed_answer:
                        continue
                    question_type = '判断题'
                    options_for_practice = None
                else:
                    # 处理选择题
                    options_for_practice = {}
                    for option_key in ['A', 'B', 'C', 'D']:
                        option_text = str(row.get(option_key, '')).strip()
                        if option_text and option_text.lower() != 'nan':
                            options_for_practice[option_key] = option_text

                    if not options_for_practice:
                        processed_answer = standardize_tf_answer(raw_answer_text)
                        if processed_answer:
                            question_type = '判断题'
                            options_for_practice = None
                        else:
                            continue
                    else:
                        processed_answer = raw_answer_text.strip().upper()
                        if processed_answer.endswith(".0"):
                            processed_answer = processed_answer[:-2]

                        # 验证答案
                        if not all(char in options_for_practice for char in processed_answer):
                            continue

                        question_type = '多选题' if len(processed_answer) > 1 else '单选题'

                questions_data.append({
                    'id': f"{filepath}_{index}",
                    'type': question_type,
                    'question': question_text,
                    'options_for_practice': options_for_practice,
                    'answer': processed_answer,
                    'is_multiple_choice': question_type == '多选题'
                })
            except Exception as e:
                logger.warning(f"Error processing question at index {index} in '{filepath}': {e}")
                continue

        logger.info(f"从文件加载 {len(questions_data)} 道题目: '{filepath}'")
        return questions_data

    except Exception as e:
        logger.error(f"Critical error loading questions from '{filepath}': {e}")
        return None


def get_all_excel_files():
    """获取所有Excel文件"""
    pattern = os.path.join(SUBJECT_DIRECTORY, "*", "*.xlsx")
    files = glob.glob(pattern)

    # 也查找直接在subject目录下的文件
    pattern_direct = os.path.join(SUBJECT_DIRECTORY, "*.xlsx")
    files.extend([f for f in glob.glob(pattern_direct) if f not in files])

    return [f.replace("\\", "/") for f in files]


def load_all_banks_from_database():
    """从数据库加载所有题目数据（主要加载方法）"""
    logger.info("从数据库加载所有题目数据...")

    try:
        # 直接从数据库获取所有题目，按题库分组
        questions_dict = get_all_questions_by_tiku_dict()
        
        if not questions_dict:
            logger.warning("数据库中没有题目数据")
            return {}

        # 统计信息
        total_questions = sum(len(questions) for questions in questions_dict.values())
        logger.info(f"从数据库成功加载 {len(questions_dict)} 个题库，共 {total_questions} 道题目")
        
        return questions_dict

    except Exception as e:
        logger.error(f"从数据库加载题目失败: {e}")
        return {}


def sync_filesystem_to_database():
    """同步文件系统的题库到数据库"""
    logger.info("开始同步文件系统到数据库...")

    # 首先从文件系统获取所有科目
    subjects_in_fs = set()
    tiku_in_fs = []

    # 扫描文件系统中的Excel文件
    excel_files = get_all_excel_files()
    
    for filepath in excel_files:
        # 解析Excel文件
        questions = load_questions_from_excel(filepath, SHEET_NAME)
        if not questions:  # 跳过空题库或解析失败的文件
            continue

        path_parts = normalize_filepath(filepath).split('/')
        if len(path_parts) >= 2:
            subject_name = path_parts[1] if len(path_parts) > 2 and path_parts[0] == SUBJECT_DIRECTORY else "未分类"
            filename = path_parts[-1].replace('.xlsx', '').replace('.xls', '')

            subjects_in_fs.add(subject_name)

            # 计算文件信息
            file_size = 0
            file_hash = None
            if os.path.exists(filepath):
                try:
                    file_size = os.path.getsize(filepath)
                    file_hash = get_file_hash(filepath)
                except Exception as e:
                    logger.warning(f"无法读取文件 {filepath}: {e}")

            tiku_in_fs.append({
                'subject_name': subject_name,
                'tiku_name': filename,
                'tiku_position': filepath,
                'tiku_nums': len(questions),
                'file_size': file_size,
                'file_hash': file_hash,
                'questions': questions  # 添加题目数据
            })

    # 同步科目到数据库
    existing_subjects = {s['subject_name']: s['subject_id'] for s in get_all_subjects()}
    subject_id_map = {}

    for subject_name in subjects_in_fs:
        if subject_name not in existing_subjects:
            result = create_subject(subject_name)
            if result['success']:
                subject_id_map[subject_name] = result['subject_id']
                logger.info(f"创建新科目: {subject_name}")
            else:
                logger.error(f"创建科目失败: {subject_name} - {result['error']}")
        else:
            subject_id_map[subject_name] = existing_subjects[subject_name]

    # 同步题库和题目到数据库
    for tiku_info in tiku_in_fs:
        subject_id = subject_id_map.get(tiku_info['subject_name'])
        if not subject_id:
            continue
            
        # 创建或更新题库记录
        result = create_or_update_tiku(
            subject_id=subject_id,
            tiku_name=tiku_info['tiku_name'],
            tiku_position=tiku_info['tiku_position'],
            tiku_nums=tiku_info['tiku_nums'],
            file_size=tiku_info['file_size'],
            file_hash=tiku_info['file_hash']
        )
        
        if result['success']:
            tiku_id = result['tiku_id']
            
            # 删除该题库的旧题目
            delete_questions_by_tiku(tiku_id)
            
            # 将题目转换为数据库格式并插入
            questions = tiku_info['questions']
            db_questions = parse_excel_to_questions(subject_id, tiku_id, questions)
            
            if db_questions:
                insert_result = insert_questions_batch(db_questions)
                if insert_result['success']:
                    logger.info(f"同步题库和题目: {tiku_info['tiku_name']} ({insert_result['inserted_count']}题)")
                else:
                    logger.error(f"同步题目失败: {tiku_info['tiku_name']} - {insert_result['error']}")
        else:
            logger.error(f"同步题库失败: {tiku_info['tiku_name']} - {result['error']}")

    logger.info("文件系统同步完成")


def startup_sync():
    """启动时同步数据库和文件系统"""
    try:
        logger.info("开始启动时同步...")

        # 检查数据库中是否有题目数据
        questions_dict = get_all_questions_by_tiku_dict()
        
        if not questions_dict:
            logger.info("数据库中没有题目数据，同步文件系统到数据库...")
            sync_filesystem_to_database()
        else:
            logger.info(f"数据库中有题目数据，共{len(questions_dict)}个题库")

        logger.info("启动时同步完成")
    except Exception as e:
        logger.warning(f"启动时同步失败: {e}") 