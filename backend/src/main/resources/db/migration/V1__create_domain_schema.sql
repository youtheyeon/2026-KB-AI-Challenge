-- 핵심 도메인 엔티티와 하위 값 객체를 저장하는 초기 데이터베이스 스키마
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT uk_users_email UNIQUE (email)
);

CREATE TABLE businesses (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    business_name VARCHAR(150) NOT NULL,
    region VARCHAR(150) NOT NULL,
    industry VARCHAR(30) NOT NULL,
    employee_count INTEGER,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT fk_business_user
        FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX idx_business_user ON businesses (user_id);

CREATE TABLE business_sales_channels (
    business_id BIGINT NOT NULL,
    sales_channel VARCHAR(30) NOT NULL,
    CONSTRAINT fk_business_sales_channel
        FOREIGN KEY (business_id) REFERENCES businesses (id)
);

CREATE TABLE datasets (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    business_id BIGINT NOT NULL,
    status VARCHAR(30) NOT NULL,
    confirmed_at TIMESTAMP(6),
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT fk_dataset_business
        FOREIGN KEY (business_id) REFERENCES businesses (id)
);

CREATE INDEX idx_dataset_business ON datasets (business_id);
CREATE INDEX idx_dataset_status ON datasets (status);

CREATE TABLE dataset_files (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    dataset_id BIGINT NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    row_count INTEGER,
    CONSTRAINT uk_dataset_file_type UNIQUE (dataset_id, file_type),
    CONSTRAINT fk_dataset_file_dataset
        FOREIGN KEY (dataset_id) REFERENCES datasets (id)
);

CREATE TABLE column_mappings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    dataset_id BIGINT NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    source_column VARCHAR(150) NOT NULL,
    target_field VARCHAR(150) NOT NULL,
    confidence DECIMAL(5, 4),
    confirmed BOOLEAN NOT NULL,
    CONSTRAINT uk_dataset_mapping_source
        UNIQUE (dataset_id, file_type, source_column),
    CONSTRAINT fk_column_mapping_dataset
        FOREIGN KEY (dataset_id) REFERENCES datasets (id)
);

CREATE TABLE diagnoses (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    business_id BIGINT NOT NULL,
    dataset_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    monthly_sales_amount BIGINT,
    operating_profit_rate DECIMAL(7, 3),
    material_cost_rate DECIMAL(7, 3),
    cash_surplus_amount BIGINT,
    monthly_order_count INTEGER,
    online_sales_ratio DECIMAL(7, 3),
    diagnosed_employee_count INTEGER,
    floating_population_growth_rate DECIMAL(7, 3),
    sales_compared_to_peer_rate DECIMAL(7, 3),
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT fk_diagnosis_business
        FOREIGN KEY (business_id) REFERENCES businesses (id),
    CONSTRAINT fk_diagnosis_dataset
        FOREIGN KEY (dataset_id) REFERENCES datasets (id)
);

CREATE INDEX idx_diagnosis_business ON diagnoses (business_id);
CREATE INDEX idx_diagnosis_dataset ON diagnoses (dataset_id);
CREATE INDEX idx_diagnosis_status ON diagnoses (status);

CREATE TABLE diagnosis_bottlenecks (
    diagnosis_id BIGINT NOT NULL,
    bottleneck_order INTEGER NOT NULL,
    bottleneck_code VARCHAR(100),
    bottleneck_title VARCHAR(200) NOT NULL,
    priority VARCHAR(30),
    confidence VARCHAR(30),
    evidence VARCHAR(1000),
    description VARCHAR(1000),
    PRIMARY KEY (diagnosis_id, bottleneck_order),
    CONSTRAINT fk_diagnosis_bottleneck
        FOREIGN KEY (diagnosis_id) REFERENCES diagnoses (id)
);

CREATE TABLE simulations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    business_id BIGINT NOT NULL,
    diagnosis_id BIGINT NOT NULL,
    loan_amount BIGINT NOT NULL,
    own_capital_amount BIGINT,
    existing_monthly_repayment_amount BIGINT,
    interest_rate DECIMAL(7, 3) NOT NULL,
    repayment_period_months INTEGER NOT NULL,
    grace_period_months INTEGER,
    repayment_type VARCHAR(30) NOT NULL,
    monthly_repayment_amount BIGINT NOT NULL,
    prediction_months INTEGER NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT fk_simulation_business
        FOREIGN KEY (business_id) REFERENCES businesses (id),
    CONSTRAINT fk_simulation_diagnosis
        FOREIGN KEY (diagnosis_id) REFERENCES diagnoses (id)
);

CREATE INDEX idx_simulation_business ON simulations (business_id);
CREATE INDEX idx_simulation_diagnosis ON simulations (diagnosis_id);

CREATE TABLE allocation_plans (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    simulation_id BIGINT NOT NULL,
    plan_code VARCHAR(5) NOT NULL,
    plan_type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    total_amount BIGINT NOT NULL,
    CONSTRAINT uk_simulation_plan_code UNIQUE (simulation_id, plan_code),
    CONSTRAINT fk_allocation_plan_simulation
        FOREIGN KEY (simulation_id) REFERENCES simulations (id)
);

CREATE TABLE allocation_plan_items (
    allocation_plan_id BIGINT NOT NULL,
    item_order INTEGER NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    amount BIGINT NOT NULL,
    expense_type VARCHAR(50),
    PRIMARY KEY (allocation_plan_id, item_order),
    CONSTRAINT fk_allocation_plan_item
        FOREIGN KEY (allocation_plan_id) REFERENCES allocation_plans (id)
);

CREATE TABLE plan_selections (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    simulation_id BIGINT NOT NULL,
    selected_plan_id BIGINT NOT NULL,
    memo VARCHAR(1000),
    verification_available_date DATE NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT uk_plan_selection_simulation UNIQUE (simulation_id),
    CONSTRAINT fk_plan_selection_simulation
        FOREIGN KEY (simulation_id) REFERENCES simulations (id),
    CONSTRAINT fk_plan_selection_plan
        FOREIGN KEY (selected_plan_id) REFERENCES allocation_plans (id)
);

CREATE INDEX idx_plan_selection_verification_date
    ON plan_selections (verification_available_date);

CREATE TABLE executions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    simulation_id BIGINT NOT NULL,
    execution_mode VARCHAR(20) NOT NULL,
    executed_at DATE NOT NULL,
    unused_amount BIGINT NOT NULL,
    total_executed_amount BIGINT NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT uk_execution_simulation UNIQUE (simulation_id),
    CONSTRAINT fk_execution_simulation
        FOREIGN KEY (simulation_id) REFERENCES simulations (id)
);

CREATE TABLE execution_items (
    execution_id BIGINT NOT NULL,
    item_order INTEGER NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    amount BIGINT NOT NULL,
    PRIMARY KEY (execution_id, item_order),
    CONSTRAINT fk_execution_item
        FOREIGN KEY (execution_id) REFERENCES executions (id)
);

CREATE TABLE outcome_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    simulation_id BIGINT NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    dataset_id BIGINT,
    monthly_sales_amount BIGINT,
    operating_profit_amount BIGINT,
    online_order_ratio DECIMAL(7, 3),
    cash_after_repayment_amount BIGINT,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT uk_outcome_data_simulation UNIQUE (simulation_id),
    CONSTRAINT fk_outcome_data_simulation
        FOREIGN KEY (simulation_id) REFERENCES simulations (id),
    CONSTRAINT fk_outcome_data_dataset
        FOREIGN KEY (dataset_id) REFERENCES datasets (id)
);

CREATE INDEX idx_outcome_data_status ON outcome_data (status);
CREATE INDEX idx_outcome_data_dataset ON outcome_data (dataset_id);

CREATE TABLE outcomes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    simulation_id BIGINT NOT NULL,
    execution_id BIGINT NOT NULL,
    outcome_data_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    sales_growth_status VARCHAR(50),
    online_ratio_status VARCHAR(50),
    cash_after_repayment_status VARCHAR(50),
    reevaluated_monthly_sales_amount BIGINT,
    reevaluated_operating_profit_amount BIGINT,
    reevaluated_cash_after_repayment_amount BIGINT,
    reevaluated_online_order_ratio DECIMAL(7, 3),
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT uk_outcome_simulation UNIQUE (simulation_id),
    CONSTRAINT uk_outcome_execution UNIQUE (execution_id),
    CONSTRAINT uk_outcome_data UNIQUE (outcome_data_id),
    CONSTRAINT fk_outcome_simulation
        FOREIGN KEY (simulation_id) REFERENCES simulations (id),
    CONSTRAINT fk_outcome_execution
        FOREIGN KEY (execution_id) REFERENCES executions (id),
    CONSTRAINT fk_outcome_data
        FOREIGN KEY (outcome_data_id) REFERENCES outcome_data (id)
);

CREATE INDEX idx_outcome_status ON outcomes (status);

CREATE TABLE outcome_monthly_sales_amounts (
    outcome_id BIGINT NOT NULL,
    metric_order INTEGER NOT NULL,
    monthly_sales_amount BIGINT NOT NULL,
    PRIMARY KEY (outcome_id, metric_order),
    CONSTRAINT fk_outcome_monthly_sales
        FOREIGN KEY (outcome_id) REFERENCES outcomes (id)
);

CREATE TABLE outcome_online_order_ratios (
    outcome_id BIGINT NOT NULL,
    metric_order INTEGER NOT NULL,
    online_order_ratio DECIMAL(7, 3) NOT NULL,
    PRIMARY KEY (outcome_id, metric_order),
    CONSTRAINT fk_outcome_online_order_ratio
        FOREIGN KEY (outcome_id) REFERENCES outcomes (id)
);

CREATE TABLE outcome_comparison_rows (
    outcome_id BIGINT NOT NULL,
    row_order INTEGER NOT NULL,
    metric_name VARCHAR(150) NOT NULL,
    scb_area VARCHAR(150),
    predicted_value VARCHAR(100),
    actual_value VARCHAR(100),
    external_factor VARCHAR(1000),
    comparison_status VARCHAR(50),
    PRIMARY KEY (outcome_id, row_order),
    CONSTRAINT fk_outcome_comparison_row
        FOREIGN KEY (outcome_id) REFERENCES outcomes (id)
);

CREATE TABLE outcome_new_bottlenecks (
    outcome_id BIGINT NOT NULL,
    bottleneck_order INTEGER NOT NULL,
    bottleneck_code VARCHAR(100),
    bottleneck_title VARCHAR(200) NOT NULL,
    priority VARCHAR(30),
    confidence VARCHAR(30),
    evidence VARCHAR(1000),
    description VARCHAR(1000),
    PRIMARY KEY (outcome_id, bottleneck_order),
    CONSTRAINT fk_outcome_new_bottleneck
        FOREIGN KEY (outcome_id) REFERENCES outcomes (id)
);
