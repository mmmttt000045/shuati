use shuati;
CREATE TABLE `user_accounts` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT COMMENT '用户唯一ID',
    `username` VARCHAR(100) NOT NULL COMMENT '用户名',
    `password_hash` VARCHAR(255) NOT NULL COMMENT '哈希后的密码',
    `is_enabled` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '账户是否可用 (1=可用, 0=禁用)',
    `used_invitation_code_id` BIGINT UNSIGNED NOT NULL COMMENT '注册时使用的邀请码ID (关联 invitation_codes.id)',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '账户创建时间',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '账户最后更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`)
    -- 外键约束将在下面通过 ALTER TABLE 添加
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户账户信息表';

CREATE TABLE `invitation_codes` (
    `id` BIGINT UNSIGNED AUTO_INCREMENT COMMENT '邀请码唯一ID',
    `code` VARCHAR(64) NOT NULL COMMENT '邀请码字符串 (例如: YAOQINGMA888)',
    `is_used` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否已被使用 (0=未使用, 1=已使用)',
    `used_by_user_id` BIGINT UNSIGNED NULL DEFAULT NULL COMMENT '使用此邀请码成功注册的用户ID (关联 user_accounts.id)',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '邀请码创建时间',
    `expires_at` TIMESTAMP NULL DEFAULT NULL COMMENT '邀请码过期时间 (可选, NULL表示永不过期)',
    -- 如果需要追踪是谁生成的邀请码，可以添加此字段:
    -- `generated_by_user_id` BIGINT UNSIGNED NULL COMMENT '生成此邀请码的用户ID (关联 user_accounts.id)',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_code` (`code`), -- 确保邀请码字符串本身是唯一的
    KEY `idx_is_used_expires_at` (`is_used`, `expires_at`) -- 用于快速查找有效且未使用的邀请码
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='邀请码信息表';