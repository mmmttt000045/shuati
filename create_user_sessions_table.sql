-- 创建用户session存储表
CREATE TABLE IF NOT EXISTS user_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_session (user_id),
    FOREIGN KEY (user_id) REFERENCES user_accounts(id) ON DELETE CASCADE,
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建清理过期session的存储过程
DELIMITER $$
CREATE PROCEDURE CleanupExpiredSessions()
BEGIN
    DELETE FROM user_sessions 
    WHERE updated_at < DATE_SUB(NOW(), INTERVAL 2 HOUR);
    
    SELECT ROW_COUNT() as cleaned_sessions;
END$$
DELIMITER ;

-- 创建定时事件来自动清理过期session（可选）
-- SET GLOBAL event_scheduler = ON;
-- 
-- CREATE EVENT IF NOT EXISTS cleanup_sessions_event
-- ON SCHEDULE EVERY 1 HOUR
-- DO
--   CALL CleanupExpiredSessions(); 