"""
工具函数模块 - 包含通用的工具函数
"""
import os
import hashlib
import logging
import math
from datetime import datetime
from typing import Optional, Any, Dict, List, Union
from flask import Response, jsonify
import pandas as pd
from .config import (
    TRUE_ANSWER_STRINGS, FALSE_ANSWER_STRINGS, 
    INTERNAL_TRUE, INTERNAL_FALSE, QUESTION_COLUMN, ANSWER_COLUMN
)

logger = logging.getLogger(__name__)


def create_response(success: bool = True, message: str = '', data: Any = None, status_code: int = 200) -> tuple[Response, int]:
    """统一的API响应格式"""
    response_data = {'success': success}
    if message:
        response_data['message'] = message
    if data is not None:
        if isinstance(data, dict):
            response_data.update(data)
        else:
            response_data['data'] = data
    return jsonify(response_data), status_code


def standardize_tf_answer(answer_text: Optional[str]) -> Optional[str]:
    """标准化判断题答案"""
    if not isinstance(answer_text, str):
        return None
    answer_upper = answer_text.strip().upper()
    if answer_upper == INTERNAL_TRUE or any(true_str.upper() == answer_upper for true_str in TRUE_ANSWER_STRINGS):
        return INTERNAL_TRUE
    if answer_upper == INTERNAL_FALSE or any(false_str.upper() == answer_upper for false_str in FALSE_ANSWER_STRINGS):
        return INTERNAL_FALSE
    return None


def is_tf_answer(answer_text: str) -> bool:
    """检查是否为判断题答案"""
    if not isinstance(answer_text, str):
        return False
    answer_upper = answer_text.strip().upper()
    return (any(true_str.upper() == answer_upper for true_str in TRUE_ANSWER_STRINGS) or
            any(false_str.upper() == answer_upper for false_str in FALSE_ANSWER_STRINGS))


def normalize_filepath(filepath: str) -> str:
    """标准化文件路径"""
    return filepath.replace("\\", "/")


def format_answer_display(answer: str, options: dict, is_multiple_choice: bool) -> str:
    """格式化答案显示"""
    if not options:
        if answer.upper() == 'T':
            return 'T. 正确'
        elif answer.upper() == 'F':
            return 'F. 错误'
        return answer

    if is_multiple_choice:
        formatted_answers = []
        for letter in sorted(answer):
            if letter in options:
                formatted_answers.append(f"{letter}. {options[letter]}")
        return " + ".join(formatted_answers)
    else:
        return f"{answer}. {options.get(answer, '')}" if answer in options else answer


def validate_answer(user_answer: str, correct_answer: str, is_multiple_choice: bool) -> bool:
    """验证用户答案是否正确"""
    user_answer = user_answer.upper()
    correct_answer = correct_answer.upper()

    if is_multiple_choice:
        return set(user_answer) == set(correct_answer)
    else:
        return user_answer == correct_answer


def get_file_hash(filepath: str) -> str:
    """计算文件MD5哈希"""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None


def ensure_subject_directory(subject_name: str, subject_directory: str = 'subject') -> str:
    """确保科目目录存在，返回目录路径"""
    subject_dir = os.path.join(subject_directory, subject_name)
    if not os.path.exists(subject_dir):
        os.makedirs(subject_dir)
    return subject_dir


def save_uploaded_file(file, subject_name: str, filename: str, subject_directory: str = 'subject') -> str:
    """保存上传的文件，返回文件路径"""
    subject_dir = ensure_subject_directory(subject_name, subject_directory)

    # 确保文件名有正确的扩展名
    if not filename.lower().endswith(('.xlsx', '.xls')):
        filename += '.xlsx'

    filepath = os.path.join(subject_dir, filename)

    # 如果文件已存在，添加时间戳
    if os.path.exists(filepath):
        base_name = filename.replace('.xlsx', '').replace('.xls', '')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f"{base_name}_{timestamp}.xlsx"
        filepath = os.path.join(subject_dir, new_filename)

    file.save(filepath)
    return normalize_filepath(filepath)


def remove_file_safely(filepath: str) -> bool:
    """安全删除文件"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"删除文件: {filepath}")
            return True
        return False
    except Exception as e:
        logger.error(f"删除文件失败 {filepath}: {e}")
        return False


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


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