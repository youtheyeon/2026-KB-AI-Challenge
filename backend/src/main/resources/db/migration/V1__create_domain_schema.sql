-- 최종 MVP 도메인 엔티티와 이력 스냅샷을 저장하는 초기 데이터베이스 스키마
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
    road_address VARCHAR(255) NOT NULL,
    industry_code VARCHAR(100) NOT NULL,
    trade_area_usage_type VARCHAR(100) NOT NULL,
    business_age VARCHAR(100) NOT NULL,
    store_type VARCHAR(100) NOT NULL,
    employee_count INTEGER NOT NULL,
    monthly_revenue_band VARCHAR(100) NOT NULL,
    seat_count INTEGER,
    average_wait_time_minutes DECIMAL(7, 2),
    peak_hour_utilization_rate DECIMAL(7, 4),
    repeat_customer_rate DECIMAL(7, 4),
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT fk_business_user
        FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX idx_business_user ON businesses (user_id);

CREATE TABLE business_sales_channels (
    business_id BIGINT NOT NULL,
    sales_channel VARCHAR(100) NOT NULL,
    PRIMARY KEY (business_id, sales_channel),
    CONSTRAINT fk_business_sales_channel
        FOREIGN KEY (business_id) REFERENCES businesses (id)
);

CREATE TABLE datasets (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    business_id BIGINT NOT NULL,
    status VARCHAR(30) NOT NULL,
    dataset_version VARCHAR(100) NOT NULL,
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
    detected_format VARCHAR(50) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
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

CREATE TABLE normalized_sales (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    dataset_id BIGINT NOT NULL,
    source_file_id BIGINT NOT NULL,
    business_date DATE NOT NULL,
    transaction_time TIME,
    receipt_number VARCHAR(100),
    pos_number VARCHAR(100),
    gross_sales BIGINT NOT NULL,
    discount_amount BIGINT NOT NULL,
    refund_amount BIGINT NOT NULL,
    net_sales BIGINT NOT NULL,
    payment_method VARCHAR(100),
    transaction_status VARCHAR(100) NOT NULL,
    CONSTRAINT fk_normalized_sale_dataset
        FOREIGN KEY (dataset_id) REFERENCES datasets (id),
    CONSTRAINT fk_normalized_sale_file
        FOREIGN KEY (source_file_id) REFERENCES dataset_files (id)
);

CREATE INDEX idx_normalized_sale_dataset_date
    ON normalized_sales (dataset_id, business_date);
CREATE INDEX idx_normalized_sale_source_file
    ON normalized_sales (source_file_id);

CREATE TABLE normalized_expenses (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    dataset_id BIGINT NOT NULL,
    source_file_id BIGINT NOT NULL,
    transaction_date DATE NOT NULL,
    counterparty VARCHAR(200),
    description VARCHAR(500),
    expense_category VARCHAR(50) NOT NULL,
    supply_amount BIGINT,
    vat_amount BIGINT,
    tax_exempt_amount BIGINT,
    total_amount BIGINT NOT NULL,
    payment_method VARCHAR(100),
    evidence_type VARCHAR(100),
    CONSTRAINT fk_normalized_expense_dataset
        FOREIGN KEY (dataset_id) REFERENCES datasets (id),
    CONSTRAINT fk_normalized_expense_file
        FOREIGN KEY (source_file_id) REFERENCES dataset_files (id)
);

CREATE INDEX idx_normalized_expense_dataset_date
    ON normalized_expenses (dataset_id, transaction_date);
CREATE INDEX idx_normalized_expense_source_file
    ON normalized_expenses (source_file_id);

CREATE TABLE normalized_online_sales (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    dataset_id BIGINT NOT NULL,
    source_file_id BIGINT NOT NULL,
    business_date DATE NOT NULL,
    sales_channel VARCHAR(100) NOT NULL,
    order_type VARCHAR(100),
    order_count INTEGER NOT NULL,
    gross_order_amount BIGINT NOT NULL,
    discount_amount BIGINT,
    refund_amount BIGINT,
    net_sales_amount BIGINT NOT NULL,
    platform_fee_amount BIGINT,
    payment_fee_amount BIGINT,
    merchant_delivery_fee BIGINT,
    settlement_amount BIGINT,
    settlement_date DATE,
    settlement_status VARCHAR(100),
    reconciliation_type VARCHAR(40) NOT NULL,
    CONSTRAINT fk_normalized_online_dataset
        FOREIGN KEY (dataset_id) REFERENCES datasets (id),
    CONSTRAINT fk_normalized_online_file
        FOREIGN KEY (source_file_id) REFERENCES dataset_files (id)
);

CREATE INDEX idx_normalized_online_dataset_date
    ON normalized_online_sales (dataset_id, business_date);
CREATE INDEX idx_normalized_online_source_file
    ON normalized_online_sales (source_file_id);

CREATE TABLE business_snapshots (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    business_id BIGINT NOT NULL,
    dataset_id BIGINT NOT NULL,
    reference_date DATE NOT NULL,
    snapshot_version VARCHAR(100) NOT NULL,
    monthly_net_sales_amount BIGINT NOT NULL,
    monthly_expense_amount BIGINT NOT NULL,
    existing_monthly_repayment_amount BIGINT NOT NULL,
    contribution_margin_rate DECIMAL(7, 4) NOT NULL,
    average_order_amount BIGINT,
    monthly_order_count INTEGER,
    online_sales_ratio DECIMAL(7, 4),
    employee_count INTEGER NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT fk_business_snapshot_business
        FOREIGN KEY (business_id) REFERENCES businesses (id),
    CONSTRAINT fk_business_snapshot_dataset
        FOREIGN KEY (dataset_id) REFERENCES datasets (id)
);

CREATE INDEX idx_business_snapshot_business_date
    ON business_snapshots (business_id, reference_date);
CREATE INDEX idx_business_snapshot_dataset
    ON business_snapshots (dataset_id);

CREATE TABLE public_data_snapshots (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    business_id BIGINT NOT NULL,
    reference_date DATE NOT NULL,
    source_name VARCHAR(200) NOT NULL,
    snapshot_version VARCHAR(100) NOT NULL,
    reference_area VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT fk_public_snapshot_business
        FOREIGN KEY (business_id) REFERENCES businesses (id)
);

CREATE INDEX idx_public_snapshot_business_date
    ON public_data_snapshots (business_id, reference_date);

CREATE TABLE diagnoses (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    business_id BIGINT NOT NULL,
    dataset_id BIGINT NOT NULL,
    business_snapshot_id BIGINT NOT NULL,
    public_data_snapshot_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    diagnosis_version VARCHAR(100) NOT NULL,
    benchmark_version VARCHAR(100) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT fk_diagnosis_business
        FOREIGN KEY (business_id) REFERENCES businesses (id),
    CONSTRAINT fk_diagnosis_dataset
        FOREIGN KEY (dataset_id) REFERENCES datasets (id),
    CONSTRAINT fk_diagnosis_business_snapshot
        FOREIGN KEY (business_snapshot_id) REFERENCES business_snapshots (id),
    CONSTRAINT fk_diagnosis_public_snapshot
        FOREIGN KEY (public_data_snapshot_id) REFERENCES public_data_snapshots (id)
);

CREATE INDEX idx_diagnosis_business ON diagnoses (business_id);
CREATE INDEX idx_diagnosis_dataset ON diagnoses (dataset_id);
CREATE INDEX idx_diagnosis_status ON diagnoses (status);
CREATE INDEX idx_diagnosis_business_snapshot
    ON diagnoses (business_snapshot_id);
CREATE INDEX idx_diagnosis_public_snapshot
    ON diagnoses (public_data_snapshot_id);

CREATE TABLE diagnosis_metrics (
    diagnosis_id BIGINT NOT NULL,
    metric_order INTEGER NOT NULL,
    metric_code VARCHAR(100) NOT NULL,
    current_value DECIMAL(19, 4) NOT NULL,
    current_source_type VARCHAR(50) NOT NULL,
    comparison_value DECIMAL(19, 4) NOT NULL,
    comparison_source_type VARCHAR(50) NOT NULL,
    difference_value DECIMAL(19, 4) NOT NULL,
    metric_unit VARCHAR(50) NOT NULL,
    metric_benchmark_version VARCHAR(100),
    PRIMARY KEY (diagnosis_id, metric_order),
    CONSTRAINT fk_diagnosis_metric
        FOREIGN KEY (diagnosis_id) REFERENCES diagnoses (id)
);

CREATE TABLE bottlenecks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    diagnosis_id BIGINT NOT NULL,
    bottleneck_order INTEGER NOT NULL,
    bottleneck_type VARCHAR(100) NOT NULL,
    detail VARCHAR(1000) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    evidence_source_type VARCHAR(50) NOT NULL,
    evidence_description VARCHAR(1000) NOT NULL,
    CONSTRAINT fk_bottleneck_diagnosis
        FOREIGN KEY (diagnosis_id) REFERENCES diagnoses (id)
);

CREATE INDEX idx_bottleneck_diagnosis
    ON bottlenecks (diagnosis_id, bottleneck_order);

CREATE TABLE bottleneck_related_categories (
    bottleneck_id BIGINT NOT NULL,
    allocation_category VARCHAR(50) NOT NULL,
    PRIMARY KEY (bottleneck_id, allocation_category),
    CONSTRAINT fk_bottleneck_related_category
        FOREIGN KEY (bottleneck_id) REFERENCES bottlenecks (id)
);

CREATE TABLE scenario_financial_results (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    monthly_loan_payment BIGINT NOT NULL,
    monthly_recurring_cost BIGINT NOT NULL,
    cash_after_payment_if_current_state_maintained BIGINT NOT NULL,
    break_even_additional_revenue BIGINT NOT NULL,
    required_additional_orders INTEGER,
    payback_period_months INTEGER,
    payback_status VARCHAR(50) NOT NULL,
    payback_reason VARCHAR(1000),
    risk_level VARCHAR(20) NOT NULL,
    source_type VARCHAR(50) NOT NULL
);

CREATE TABLE scenario_risk_reasons (
    financial_result_id BIGINT NOT NULL,
    reason_order INTEGER NOT NULL,
    risk_reason VARCHAR(1000) NOT NULL,
    PRIMARY KEY (financial_result_id, reason_order),
    CONSTRAINT fk_scenario_risk_reason
        FOREIGN KEY (financial_result_id) REFERENCES scenario_financial_results (id)
);

CREATE TABLE simulations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    business_id BIGINT NOT NULL,
    dataset_id BIGINT NOT NULL,
    diagnosis_id BIGINT NOT NULL,
    business_snapshot_id BIGINT NOT NULL,
    loan_amount BIGINT NOT NULL,
    annual_interest_rate DECIMAL(7, 4) NOT NULL,
    term_months INTEGER NOT NULL,
    grace_months INTEGER NOT NULL,
    repayment_type VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL,
    allocation_generator_version VARCHAR(100) NOT NULL,
    calculation_version VARCHAR(100) NOT NULL,
    prompt_version VARCHAR(100) NOT NULL,
    public_data_reference_date DATE NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT fk_simulation_business
        FOREIGN KEY (business_id) REFERENCES businesses (id),
    CONSTRAINT fk_simulation_dataset
        FOREIGN KEY (dataset_id) REFERENCES datasets (id),
    CONSTRAINT fk_simulation_diagnosis
        FOREIGN KEY (diagnosis_id) REFERENCES diagnoses (id),
    CONSTRAINT fk_simulation_business_snapshot
        FOREIGN KEY (business_snapshot_id) REFERENCES business_snapshots (id),
    CONSTRAINT ck_simulation_loan_amount
        CHECK (loan_amount > 0),
    CONSTRAINT ck_simulation_interest_rate
        CHECK (annual_interest_rate >= 0),
    CONSTRAINT ck_simulation_term_months
        CHECK (term_months > 0),
    CONSTRAINT ck_simulation_grace_months
        CHECK (grace_months >= 0 AND grace_months <= term_months)
);

CREATE INDEX idx_simulation_business ON simulations (business_id);
CREATE INDEX idx_simulation_dataset ON simulations (dataset_id);
CREATE INDEX idx_simulation_diagnosis ON simulations (diagnosis_id);
CREATE INDEX idx_simulation_business_snapshot
    ON simulations (business_snapshot_id);

CREATE TABLE scenarios (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    simulation_id BIGINT NOT NULL,
    scenario_code VARCHAR(5) NOT NULL,
    strategy_type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    total_amount BIGINT NOT NULL,
    financial_result_id BIGINT NOT NULL,
    CONSTRAINT uk_simulation_scenario_code
        UNIQUE (simulation_id, scenario_code),
    CONSTRAINT uk_scenario_financial_result
        UNIQUE (financial_result_id),
    CONSTRAINT fk_scenario_simulation
        FOREIGN KEY (simulation_id) REFERENCES simulations (id),
    CONSTRAINT fk_scenario_financial_result
        FOREIGN KEY (financial_result_id) REFERENCES scenario_financial_results (id)
);

CREATE TABLE scenario_allocations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    scenario_id BIGINT NOT NULL,
    allocation_order INTEGER NOT NULL,
    category VARCHAR(50) NOT NULL,
    ratio DECIMAL(7, 4) NOT NULL,
    amount BIGINT NOT NULL,
    CONSTRAINT uk_scenario_allocation_category
        UNIQUE (scenario_id, category),
    CONSTRAINT fk_scenario_allocation
        FOREIGN KEY (scenario_id) REFERENCES scenarios (id),
    CONSTRAINT ck_scenario_allocation_ratio
        CHECK (ratio >= 0),
    CONSTRAINT ck_scenario_allocation_amount
        CHECK (amount >= 0)
);

CREATE INDEX idx_scenario_allocation_order
    ON scenario_allocations (scenario_id, allocation_order);

CREATE TABLE scenario_draft_reasons (
    scenario_id BIGINT NOT NULL,
    reason_order INTEGER NOT NULL,
    bottleneck_type VARCHAR(100) NOT NULL,
    related_category VARCHAR(50) NOT NULL,
    description VARCHAR(1000) NOT NULL,
    PRIMARY KEY (scenario_id, reason_order),
    CONSTRAINT fk_scenario_draft_reason
        FOREIGN KEY (scenario_id) REFERENCES scenarios (id)
);

CREATE TABLE scenario_target_metrics (
    scenario_id BIGINT NOT NULL,
    metric_order INTEGER NOT NULL,
    target_metric VARCHAR(100) NOT NULL,
    PRIMARY KEY (scenario_id, metric_order),
    CONSTRAINT fk_scenario_target_metric
        FOREIGN KEY (scenario_id) REFERENCES scenarios (id)
);

CREATE TABLE scenario_selections (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    simulation_id BIGINT NOT NULL,
    selected_scenario_id BIGINT NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT uk_scenario_selection_simulation UNIQUE (simulation_id),
    CONSTRAINT fk_scenario_selection_simulation
        FOREIGN KEY (simulation_id) REFERENCES simulations (id),
    CONSTRAINT fk_scenario_selection_scenario
        FOREIGN KEY (selected_scenario_id) REFERENCES scenarios (id)
);

CREATE INDEX idx_scenario_selection_scenario
    ON scenario_selections (selected_scenario_id);

CREATE TABLE executions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    simulation_id BIGINT NOT NULL,
    scenario_selection_id BIGINT NOT NULL,
    execution_type VARCHAR(30) NOT NULL,
    executed_at DATE NOT NULL,
    unused_amount BIGINT NOT NULL,
    total_executed_amount BIGINT NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT uk_execution_simulation UNIQUE (simulation_id),
    CONSTRAINT uk_execution_selection UNIQUE (scenario_selection_id),
    CONSTRAINT fk_execution_simulation
        FOREIGN KEY (simulation_id) REFERENCES simulations (id),
    CONSTRAINT fk_execution_selection
        FOREIGN KEY (scenario_selection_id) REFERENCES scenario_selections (id),
    CONSTRAINT ck_execution_unused_amount
        CHECK (unused_amount >= 0),
    CONSTRAINT ck_execution_total_amount
        CHECK (total_executed_amount >= 0)
);

CREATE TABLE execution_allocations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    execution_id BIGINT NOT NULL,
    allocation_order INTEGER NOT NULL,
    category VARCHAR(50) NOT NULL,
    amount BIGINT NOT NULL,
    CONSTRAINT uk_execution_allocation_category
        UNIQUE (execution_id, category),
    CONSTRAINT fk_execution_allocation
        FOREIGN KEY (execution_id) REFERENCES executions (id),
    CONSTRAINT ck_execution_allocation_amount
        CHECK (amount >= 0)
);

CREATE INDEX idx_execution_allocation_order
    ON execution_allocations (execution_id, allocation_order);

CREATE TABLE outcome_data (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    simulation_id BIGINT NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    dataset_id BIGINT,
    observed_business_snapshot_id BIGINT NOT NULL,
    observed_at DATE NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT uk_outcome_data_simulation UNIQUE (simulation_id),
    CONSTRAINT fk_outcome_data_simulation
        FOREIGN KEY (simulation_id) REFERENCES simulations (id),
    CONSTRAINT fk_outcome_data_dataset
        FOREIGN KEY (dataset_id) REFERENCES datasets (id),
    CONSTRAINT fk_outcome_data_business_snapshot
        FOREIGN KEY (observed_business_snapshot_id) REFERENCES business_snapshots (id)
);

CREATE INDEX idx_outcome_data_status ON outcome_data (status);
CREATE INDEX idx_outcome_data_dataset ON outcome_data (dataset_id);
CREATE INDEX idx_outcome_data_business_snapshot
    ON outcome_data (observed_business_snapshot_id);

CREATE TABLE reassessment_snapshots (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    latest_business_snapshot_id BIGINT NOT NULL,
    CONSTRAINT fk_reassessment_business_snapshot
        FOREIGN KEY (latest_business_snapshot_id) REFERENCES business_snapshots (id)
);

CREATE INDEX idx_reassessment_business_snapshot
    ON reassessment_snapshots (latest_business_snapshot_id);

CREATE TABLE reassessment_resolved_bottlenecks (
    reassessment_snapshot_id BIGINT NOT NULL,
    bottleneck_type VARCHAR(100) NOT NULL,
    PRIMARY KEY (reassessment_snapshot_id, bottleneck_type),
    CONSTRAINT fk_reassessment_resolved
        FOREIGN KEY (reassessment_snapshot_id) REFERENCES reassessment_snapshots (id)
);

CREATE TABLE reassessment_remaining_bottlenecks (
    reassessment_snapshot_id BIGINT NOT NULL,
    bottleneck_type VARCHAR(100) NOT NULL,
    PRIMARY KEY (reassessment_snapshot_id, bottleneck_type),
    CONSTRAINT fk_reassessment_remaining
        FOREIGN KEY (reassessment_snapshot_id) REFERENCES reassessment_snapshots (id)
);

CREATE TABLE reassessment_new_bottlenecks (
    reassessment_snapshot_id BIGINT NOT NULL,
    bottleneck_type VARCHAR(100) NOT NULL,
    PRIMARY KEY (reassessment_snapshot_id, bottleneck_type),
    CONSTRAINT fk_reassessment_new
        FOREIGN KEY (reassessment_snapshot_id) REFERENCES reassessment_snapshots (id)
);

CREATE TABLE outcome_comparisons (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    simulation_id BIGINT NOT NULL,
    execution_id BIGINT NOT NULL,
    outcome_data_id BIGINT NOT NULL,
    reassessment_snapshot_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    CONSTRAINT uk_outcome_comparison_simulation UNIQUE (simulation_id),
    CONSTRAINT uk_outcome_comparison_execution UNIQUE (execution_id),
    CONSTRAINT uk_outcome_comparison_data UNIQUE (outcome_data_id),
    CONSTRAINT uk_outcome_comparison_reassessment
        UNIQUE (reassessment_snapshot_id),
    CONSTRAINT fk_outcome_comparison_simulation
        FOREIGN KEY (simulation_id) REFERENCES simulations (id),
    CONSTRAINT fk_outcome_comparison_execution
        FOREIGN KEY (execution_id) REFERENCES executions (id),
    CONSTRAINT fk_outcome_comparison_data
        FOREIGN KEY (outcome_data_id) REFERENCES outcome_data (id),
    CONSTRAINT fk_outcome_comparison_reassessment
        FOREIGN KEY (reassessment_snapshot_id) REFERENCES reassessment_snapshots (id)
);

CREATE INDEX idx_outcome_comparison_status
    ON outcome_comparisons (status);

CREATE TABLE outcome_comparison_rows (
    outcome_comparison_id BIGINT NOT NULL,
    row_order INTEGER NOT NULL,
    metric_code VARCHAR(150) NOT NULL,
    target_condition VARCHAR(255),
    observed_value VARCHAR(255),
    change_value VARCHAR(255),
    result_status VARCHAR(50) NOT NULL,
    external_factors VARCHAR(1000),
    PRIMARY KEY (outcome_comparison_id, row_order),
    CONSTRAINT fk_outcome_comparison_row
        FOREIGN KEY (outcome_comparison_id) REFERENCES outcome_comparisons (id)
);
