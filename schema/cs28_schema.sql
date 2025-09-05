SET NAMES utf8mb4;
SET time_zone = '+08:00';

CREATE TABLE IF NOT EXISTS sys_kv_config (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  k             VARCHAR(64)  NOT NULL UNIQUE,
  v             VARCHAR(512) NOT NULL,
  remark        VARCHAR(255) NULL,
  is_active     TINYINT(1) NOT NULL DEFAULT 1,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user (
  id                 BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  username           VARCHAR(64)  NOT NULL UNIQUE,
  password_hash      VARCHAR(255) NOT NULL,
  nickname           VARCHAR(64)  NULL,
  avatar_url         VARCHAR(255) NULL,
  mobile             VARCHAR(32)  NULL,
  email              VARCHAR(128) NULL,
  status             TINYINT NOT NULL DEFAULT 1,
  is_robot           TINYINT(1) NOT NULL DEFAULT 0,
  register_ip        VARCHAR(64)  NULL,
  last_login_ip      VARCHAR(64)  NULL,
  last_login_time    DATETIME NULL,
  last_login_device  VARCHAR(64)  NULL,
  last_login_city    VARCHAR(64)  NULL,
  balance            DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  frozen_balance     DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  total_bet_amount   DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  total_payout       DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  total_profit       DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  total_orders       INT NOT NULL DEFAULT 0,
  remark             VARCHAR(255) NULL,
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_user_username (username),
  INDEX idx_user_mobile (mobile)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wallet_account (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id       BIGINT UNSIGNED NOT NULL UNIQUE,
  available     DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  frozen        DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  version       INT NOT NULL DEFAULT 0,
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wallet_ledger (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id         BIGINT UNSIGNED NOT NULL,
  direction       TINYINT NOT NULL,
  amount          DECIMAL(16,2) NOT NULL,
  balance_after   DECIMAL(16,2) NOT NULL,
  biz_type        TINYINT NOT NULL,
  ref_table       VARCHAR(32)  NULL,
  ref_id          BIGINT UNSIGNED NULL,
  remark          VARCHAR(255) NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ledger_user_time (user_id, created_at),
  INDEX idx_ledger_ref (ref_table, ref_id),
  FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lottery (
  id                 BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  code               VARCHAR(32) NOT NULL UNIQUE,
  name               VARCHAR(64) NOT NULL,
  period_seconds     INT NOT NULL DEFAULT 210,
  lock_ahead_seconds INT NOT NULL DEFAULT 3,
  status             TINYINT NOT NULL DEFAULT 1,
  tz                 VARCHAR(32) NOT NULL DEFAULT 'Asia/Shanghai',
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS issue (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  lottery_code    VARCHAR(32) NOT NULL,
  issue_code      VARCHAR(32) NOT NULL,
  open_time       DATETIME NOT NULL,
  close_time      DATETIME NOT NULL,
  status          TINYINT NOT NULL DEFAULT 1,
  n1              TINYINT NULL,
  n2              TINYINT NULL,
  n3              TINYINT NULL,
  sum_value       TINYINT NULL,
  bs              TINYINT NULL,
  oe              TINYINT NULL,
  extreme         TINYINT NULL,
  raw_json        VARCHAR(255) NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_issue (lottery_code, issue_code),
  INDEX idx_issue_status (lottery_code, status, open_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
