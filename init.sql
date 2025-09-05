-- 建议：先执行
-- SET NAMES utf8mb4;
-- SET time_zone = '+08:00';

-- 1. 系统配置/字典 ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS sys_kv_config (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  k             VARCHAR(64)  NOT NULL UNIQUE,
  v             VARCHAR(512) NOT NULL,
  remark        VARCHAR(255) NULL,
  is_active     TINYINT(1) NOT NULL DEFAULT 1,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sys_sensi_words (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  word          VARCHAR(64) NOT NULL UNIQUE,
  level         TINYINT NOT NULL DEFAULT 1, -- 1提示 2禁言
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 用户/认证/登录记录 ----------------------------------------------------
CREATE TABLE IF NOT EXISTS user (
  id                 BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  username           VARCHAR(64)  NOT NULL UNIQUE,
  password_hash      VARCHAR(255) NOT NULL,
  nickname           VARCHAR(64)  NULL,
  avatar_url         VARCHAR(255) NULL,
  mobile             VARCHAR(32)  NULL,
  email              VARCHAR(128) NULL,
  status             TINYINT NOT NULL DEFAULT 1,      -- 1正常 0禁用
  is_robot           TINYINT(1) NOT NULL DEFAULT 0,
  register_ip        VARCHAR(64)  NULL,
  last_login_ip      VARCHAR(64)  NULL,
  last_login_time    DATETIME NULL,
  last_login_device  VARCHAR(64)  NULL,
  last_login_city    VARCHAR(64)  NULL,

  -- 冗余统计
  balance            DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  frozen_balance     DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  total_bet_amount   DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  total_payout       DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  total_profit       DECIMAL(16,2) NOT NULL DEFAULT 0.00, -- 派彩-投注
  total_orders       INT NOT NULL DEFAULT 0,

  remark             VARCHAR(255) NULL,
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_user_username (username),
  INDEX idx_user_mobile (mobile)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_login_log (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id       BIGINT UNSIGNED NOT NULL,
  login_time    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  login_ip      VARCHAR(64) NOT NULL,
  device        VARCHAR(64) NULL,
  ua            VARCHAR(255) NULL,
  city          VARCHAR(64) NULL,
  success       TINYINT(1) NOT NULL DEFAULT 1,
  reason        VARCHAR(128) NULL,
  FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 钱包（账户+资金流水） --------------------------------------------------
CREATE TABLE IF NOT EXISTS wallet_account (
  id            BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id       BIGINT UNSIGNED NOT NULL UNIQUE,
  available     DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  frozen        DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  version       INT NOT NULL DEFAULT 0, -- 乐观锁
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 资金流水：方向（1入账/2出账），类型/业务类型可扩展
CREATE TABLE IF NOT EXISTS wallet_ledger (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id         BIGINT UNSIGNED NOT NULL,
  direction       TINYINT NOT NULL,              -- 1入 2出
  amount          DECIMAL(16,2) NOT NULL,        -- 正数
  balance_after   DECIMAL(16,2) NOT NULL,
  biz_type        TINYINT NOT NULL,              -- 10充值 11提现 20下注 21撤单返还 30派彩 31活动 40调整
  ref_table       VARCHAR(32)  NULL,             -- 关联表：orders/withdraw/...
  ref_id          BIGINT UNSIGNED NULL,
  remark          VARCHAR(255) NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ledger_user_time (user_id, created_at),
  INDEX idx_ledger_ref (ref_table, ref_id),
  FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 彩种/玩法 -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lottery (
  id                 BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  code               VARCHAR(32) NOT NULL UNIQUE, -- jnd28 等
  name               VARCHAR(64) NOT NULL,
  period_seconds     INT NOT NULL DEFAULT 210,    -- 3分半=210秒
  lock_ahead_seconds INT NOT NULL DEFAULT 3,      -- 封盘提前秒
  status             TINYINT NOT NULL DEFAULT 1,  -- 1启用 0停用
  tz                 VARCHAR(32) NOT NULL DEFAULT 'Asia/Shanghai',
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 玩法字典（示例：大小单双、极值等）
CREATE TABLE IF NOT EXISTS play_type (
  id            INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  lottery_code  VARCHAR(32) NOT NULL,           -- 分彩种可差异化
  code          INT NOT NULL,                   -- 28-37 等内部枚举
  name          VARCHAR(64) NOT NULL,
  odds          DECIMAL(10,4) NOT NULL DEFAULT 1.9800,
  status        TINYINT NOT NULL DEFAULT 1,
  UNIQUE KEY uk_play (lottery_code, code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 期号/开奖记录 ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS issue (
  id              BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  lottery_code    VARCHAR(32) NOT NULL,
  issue_code      VARCHAR(32) NOT NULL,         -- 期号
  open_time       DATETIME NOT NULL,            -- 开奖时间（官方）
  close_time      DATETIME NOT NULL,            -- 封盘时间 = open_time - lock_ahead
  status          TINYINT NOT NULL DEFAULT 1,   -- 1销售中 2封盘 3已开奖 4已结算 9作废
  -- 开奖结果
  n1              TINYINT NULL,
  n2              TINYINT NULL,
  n3              TINYINT NULL,
  sum_value       TINYINT NULL,                 -- 0~27
  bs              TINYINT NULL,                 -- 1大 2小
  oe              TINYINT NULL,                 -- 1单 2双
  extreme         TINYINT NULL,                 -- 1极大 2极小 0否
  raw_json        VARCHAR(255) NULL,            -- 原始采集记录（可截断）
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_issue (lottery_code, issue_code),
  INDEX idx_issue_status (lottery_code, status, open_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. 下注订单（主+明细） ---------------------------------------------------
-- 主订单
CREATE TABLE IF NOT EXISTS orders (
  id               BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id          BIGINT UNSIGNED NOT NULL,
  lottery_code     VARCHAR(32) NOT NULL,
  issue_code       VARCHAR(32) NOT NULL,
  total_amount     DECIMAL(16,2) NOT NULL,
  total_odds       DECIMAL(10,4) NULL,          -- 可选：组合玩法
  status           TINYINT NOT NULL DEFAULT 1,   -- 1已提交 2已撤单 3待结算 4已派彩 5未中奖 9作废
  win_amount       DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  ip               VARCHAR(64) NULL,
  channel          VARCHAR(32) NULL,             -- web/h5/ios/android/robot
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_order_user_time (user_id, created_at),
  INDEX idx_order_issue (lottery_code, issue_code),
  FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 明细（支持多条：大300丨小300）
CREATE TABLE IF NOT EXISTS order_item (
  id               BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  order_id         BIGINT UNSIGNED NOT NULL,
  play_code        INT NOT NULL,                 -- 对应 play_type.code
  selection        VARCHAR(32) NOT NULL,         -- 具体选项，如 "大"/"小"/"单"/"双"/"0~27"
  odds             DECIMAL(10,4) NOT NULL,
  stake_amount     DECIMAL(16,2) NOT NULL,
  result_status    TINYINT NOT NULL DEFAULT 0,   -- 0未结算 1赢 2输 3和/取消
  win_amount       DECIMAL(16,2) NOT NULL DEFAULT 0.00,
  settled_at       DATETIME NULL,
  UNIQUE KEY uk_order_play_sel (order_id, play_code, selection),
  INDEX idx_item_order (order_id),
  FOREIGN KEY (order_id) REFERENCES orders(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 撤单记录（冗余以便审计）
CREATE TABLE IF NOT EXISTS order_cancel_log (
  id               BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  order_id         BIGINT UNSIGNED NOT NULL,
  user_id          BIGINT UNSIGNED NOT NULL,
  reason           VARCHAR(128) NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (order_id) REFERENCES orders(id),
  FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. 充值/提现（可选，先放结构） ------------------------------------------
CREATE TABLE IF NOT EXISTS deposit_order (
  id               BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id          BIGINT UNSIGNED NOT NULL,
  amount           DECIMAL(16,2) NOT NULL,
  status           TINYINT NOT NULL DEFAULT 0, -- 0待支付 1成功 2失败
  channel          VARCHAR(32) NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS withdraw_order (
  id               BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id          BIGINT UNSIGNED NOT NULL,
  amount           DECIMAL(16,2) NOT NULL,
  status           TINYINT NOT NULL DEFAULT 0, -- 0申请 1通过 2驳回 3已打款
  channel          VARCHAR(32) NULL,
  account_info     VARCHAR(255) NULL,
  remark           VARCHAR(255) NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. 结算与任务日志 --------------------------------------------------------
CREATE TABLE IF NOT EXISTS settle_log (
  id               BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  lottery_code     VARCHAR(32) NOT NULL,
  issue_code       VARCHAR(32) NOT NULL,
  status           TINYINT NOT NULL,            -- 1开始 2完成 3失败
  message          VARCHAR(255) NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_settle_issue (lottery_code, issue_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS job_run_log (
  id               BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  job_name         VARCHAR(64) NOT NULL,        -- collector_jnd28 / auto_settle 等
  status           TINYINT NOT NULL,            -- 1成功 2失败
  detail           VARCHAR(255) NULL,
  started_at       DATETIME NOT NULL,
  finished_at      DATETIME NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_job_time (job_name, started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. 风控（频控/黑名单等，可扩） ------------------------------------------
CREATE TABLE IF NOT EXISTS risk_user_flag (
  id               BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id          BIGINT UNSIGNED NOT NULL,
  flag_code        VARCHAR(32) NOT NULL,        -- e.g. "BET_TOO_FAST"
  note             VARCHAR(255) NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_risk (user_id, flag_code),
  FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
