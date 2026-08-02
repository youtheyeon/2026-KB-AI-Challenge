/* eslint-disable */
/* tslint:disable */
// @ts-nocheck
/*
 * ---------------------------------------------------------------
 * ## THIS FILE WAS GENERATED VIA SWAGGER-TYPESCRIPT-API        ##
 * ##                                                           ##
 * ## AUTHOR: acacode                                           ##
 * ## SOURCE: https://github.com/acacode/swagger-typescript-api ##
 * ---------------------------------------------------------------
 */

/** ActivityMetricsResponse */
export interface ActivityMetricsResponse {
  /** Employeecount */
  employeeCount: number;
  /** Monthlyordercount */
  monthlyOrderCount: number;
  /** Onlinesalesratio */
  onlineSalesRatio: number | null;
}

/** AllocationResponse */
export interface AllocationResponse {
  /** Amount */
  amount: number;
  /** Category */
  category: string;
  /** Ratio */
  ratio: number;
}

/** Body_upload_dataset_api_businesses__business_id__datasets_post */
export interface BodyUploadDatasetApiBusinessesBusinessIdDatasetsPost {
  /** Expensefile */
  expenseFile: File | Blob;
  /** Onlinesalesfile */
  onlineSalesFile?: File | Blob | null;
  /** Salesfile */
  salesFile: File | Blob;
}

/** BottleneckResponse */
export interface BottleneckResponse {
  /** Code */
  code: string;
  /** Confidence */
  confidence: "LOW" | "MEDIUM" | "HIGH";
  /** Evidence */
  evidence: string;
  /** Priority */
  priority: "LOW" | "MEDIUM" | "HIGH";
  /** Title */
  title: string;
}

/** BusinessRegistrationRequest */
export interface BusinessRegistrationRequest {
  /**
   * Employeecount
   * @min 0
   * @max 2147483647
   * @default 0
   */
  employeeCount?: number;
  /**
   * Industry
   * @minLength 1
   * @maxLength 100
   */
  industry: string;
  /**
   * Name
   * @minLength 1
   * @maxLength 150
   */
  name: string;
  /** Primarysaleschannels */
  primarySalesChannels?: string[];
  /**
   * Region
   * @minLength 1
   * @maxLength 255
   */
  region: string;
}

/** BusinessRegistrationResponse */
export interface BusinessRegistrationResponse {
  /** Businessid */
  businessId: number;
  /** Employeecount */
  employeeCount: number;
  /** Industry */
  industry: string;
  /** Name */
  name: string;
  /** Primarysaleschannels */
  primarySalesChannels: string[];
  /** Region */
  region: string;
}

/** CommercialMetricsResponse */
export interface CommercialMetricsResponse {
  /** Floatingpopulationgrowthrate */
  floatingPopulationGrowthRate: number | null;
  /** Salescomparedtopeerrate */
  salesComparedToPeerRate: number;
}

/** ComparisonRowResponse */
export interface ComparisonRowResponse {
  /** Breakevenvalue */
  breakEvenValue: number | null;
  /** Label */
  label: string;
  /** Metriccode */
  metricCode: string;
  /** Observedvalue */
  observedValue: number | null;
  /** Status */
  status: string;
  /** Targetvalue */
  targetValue: number | null;
  /** Unit */
  unit: string;
}

/** CycleHistoryResponse */
export interface CycleHistoryResponse {
  execution: ExecutionCycleResponse | null;
  outcome: OutcomeCycleResponse;
  selectedPlan: SelectedPlanResponse | null;
  /**
   * Simulatedat
   * @format date-time
   */
  simulatedAt: string;
  /** Simulationid */
  simulationId: number;
}

/** DashboardBusinessResponse */
export interface DashboardBusinessResponse {
  /** Businessid */
  businessId: number;
  /** Industry */
  industry: string;
  /** Name */
  name: string;
  /** Region */
  region: string;
}

/** DashboardMetricTrendResponse */
export interface DashboardMetricTrendResponse {
  /** Aftervalue */
  afterValue: number | null;
  /** Beforevalue */
  beforeValue: number | null;
  /** Metriccode */
  metricCode: string;
  /**
   * Recordedat
   * @format date-time
   */
  recordedAt: string;
  /** Simulationid */
  simulationId: number;
  /** Status */
  status: string;
  /** Unit */
  unit: string;
}

/** DashboardResponse */
export interface DashboardResponse {
  business: DashboardBusinessResponse;
  /** Cyclehistories */
  cycleHistories: CycleHistoryResponse[];
  loanStatus: LoanStatusResponse | null;
  /** Metrictrends */
  metricTrends: DashboardMetricTrendResponse[];
  /** Nextinitialconditions */
  nextInitialConditions: Record<string, any> | null;
  /** Unresolvedbottlenecks */
  unresolvedBottlenecks: UnresolvedBottleneckResponse[];
}

/** DatasetFileStatusResponse */
export interface DatasetFileStatusResponse {
  /** Columnmapping */
  columnMapping: Record<string, string>;
  detectedFormat: DatasetFormat;
  fileType: DatasetFileType;
  /** Mappingconfidence */
  mappingConfidence: number;
  /** Missingcolumns */
  missingColumns: string[];
  /** Originalfilename */
  originalFilename: string;
  /** Rowcount */
  rowCount: number;
}

/** DatasetFileType */
export enum DatasetFileType {
  Sale = "sale",
  Expense = "expense",
  OnlineSale = "online_sale",
}

/** DatasetFormat */
export enum DatasetFormat {
  EasyposSales = "easypos_sales",
  EasyshopExpenseLedger = "easyshop_expense_ledger",
  EasyshopOnlineSales = "easyshop_online_sales",
  Unknown = "unknown",
}

/** DatasetStatus */
export enum DatasetStatus {
  Uploaded = "uploaded",
  Parsing = "parsing",
  Normalizing = "normalizing",
  Ready = "ready",
  NeedsReupload = "needs_reupload",
  Failed = "failed",
}

/** DatasetStatusResponse */
export interface DatasetStatusResponse {
  /** Businessid */
  businessId: number;
  /** Datasetid */
  datasetId: number;
  /** Files */
  files: DatasetFileStatusResponse[];
  status: DatasetStatus;
}

/** DatasetUploadResponse */
export interface DatasetUploadResponse {
  /** Datasetid */
  datasetId: number;
  status: DatasetStatus;
}

/** DiagnosisResultResponse */
export interface DiagnosisResultResponse {
  activityMetrics?: ActivityMetricsResponse | null;
  /** Bottlenecks */
  bottlenecks?: BottleneckResponse[] | null;
  commercialMetrics?: CommercialMetricsResponse | null;
  /** Diagnosisid */
  diagnosisId: number;
  financialMetrics?: FinancialMetricsResponse | null;
  /** Status */
  status: "RUNNING" | "COMPLETED" | "FAILED";
}

/** DiagnosisStartRequest */
export interface DiagnosisStartRequest {
  /**
   * Datasetid
   * @exclusiveMin 0
   */
  datasetId: number;
}

/** DiagnosisStartResponse */
export interface DiagnosisStartResponse {
  /** Businessid */
  businessId: number;
  /**
   * Createdat
   * @format date-time
   */
  createdAt: string;
  /** Diagnosisid */
  diagnosisId: number;
  /** Status */
  status: "RUNNING";
}

/** ExecutionCreatedResponse */
export interface ExecutionCreatedResponse {
  /** Executionid */
  executionId: number;
  /** Executionmode */
  executionMode: string;
  /**
   * Savedat
   * @format date-time
   */
  savedAt: string;
  /** Simulationid */
  simulationId: number;
  /** Totalexecutedamount */
  totalExecutedAmount: number;
}

/** ExecutionCreationRequest */
export interface ExecutionCreationRequest {
  /**
   * Executedat
   * @format date
   */
  executedAt: string;
  executionMode: ExecutionModeRequest;
  /** Items */
  items?: ExecutionItemRequest[];
  /** Note */
  note?: string | null;
  /**
   * Unusedamount
   * @min 0
   * @max 9223372036854776000
   */
  unusedAmount: number;
}

/** ExecutionCycleResponse */
export interface ExecutionCycleResponse {
  /** Executedat */
  executedAt: string | null;
  /** Executionid */
  executionId: number;
  /** Executionmode */
  executionMode: string;
  /** Totalexecutedamount */
  totalExecutedAmount: number;
  /** Unusedamount */
  unusedAmount: number;
}

/** ExecutionItemRequest */
export interface ExecutionItemRequest {
  /**
   * Amount
   * @exclusiveMin 0
   * @max 9223372036854776000
   */
  amount: number;
  /**
   * Name
   * @minLength 1
   * @maxLength 255
   */
  name: string;
}

/** ExecutionModeRequest */
export enum ExecutionModeRequest {
  SAME_AS_A = "SAME_AS_A",
  SAME_AS_B = "SAME_AS_B",
  SAME_AS_C = "SAME_AS_C",
  MIXED = "MIXED",
  CUSTOM = "CUSTOM",
}

/** FinancialMetricsResponse */
export interface FinancialMetricsResponse {
  /** Cashsurplusamount */
  cashSurplusAmount: number;
  /** Materialcostrate */
  materialCostRate: number;
  /** Monthlysalesamount */
  monthlySalesAmount: number;
  /** Operatingprofitrate */
  operatingProfitRate: number;
}

/** FinancialResultResponse */
export interface FinancialResultResponse {
  /** Breakevenadditionalrevenue */
  breakEvenAdditionalRevenue: number | null;
  /** Cashafterpayment */
  cashAfterPayment: number | null;
  /** Monthlyloanpayment */
  monthlyLoanPayment: number | null;
  /** Monthlyrecurringcost */
  monthlyRecurringCost: number | null;
  /** Paybackperiodmonths */
  paybackPeriodMonths: number | null;
  /** Requiredadditionalorders */
  requiredAdditionalOrders: number | null;
  /** Risklevel */
  riskLevel: string | null;
}

/** HTTPValidationError */
export interface HTTPValidationError {
  /** Detail */
  detail?: ValidationError[];
}

/** HealthResponse */
export interface HealthResponse {
  /** Status */
  status: "ok";
}

/** LoanConditionResponse */
export interface LoanConditionResponse {
  /** Amount */
  amount: number;
  /** Annualinterestrate */
  annualInterestRate: number;
  /** Gracemonths */
  graceMonths: number;
  /** Repaymenttype */
  repaymentType: string;
  /** Termmonths */
  termMonths: number;
}

/** LoanStatusResponse */
export interface LoanStatusResponse {
  /** Estimatedremainingprincipal */
  estimatedRemainingPrincipal: number;
  /** Loanamount */
  loanAmount: number;
  /** Monthlyrepaymentamount */
  monthlyRepaymentAmount: number;
  /** Paidamount */
  paidAmount: number;
  /** Progressrate */
  progressRate: number;
  /** Repaymentdatatype */
  repaymentDataType: string;
}

/** MetricTrendResponse */
export interface MetricTrendResponse {
  /** Aftervalue */
  afterValue: number | null;
  /** Beforevalue */
  beforeValue: number | null;
  /** Metriccode */
  metricCode: string;
  /** Unit */
  unit: string;
}

/** NewBottleneckResponse */
export interface NewBottleneckResponse {
  /** Bottlenecktype */
  bottleneckType: string;
  /** Detail */
  detail: string | null;
  /** Title */
  title: string;
}

/** OutcomeCreatedResponse */
export interface OutcomeCreatedResponse {
  /**
   * Createdat
   * @format date-time
   */
  createdAt: string;
  /** Outcomeid */
  outcomeId: number;
  /** Simulationid */
  simulationId: number;
  /** Status */
  status: string;
  summary: OutcomeSummaryResponse;
}

/** OutcomeCreationRequest */
export interface OutcomeCreationRequest {
  /**
   * Executionid
   * @exclusiveMin 0
   */
  executionId: number;
  /**
   * Outcomedataid
   * @exclusiveMin 0
   */
  outcomeDataId: number;
}

/** OutcomeCycleResponse */
export interface OutcomeCycleResponse {
  /**
   * Completedat
   * @format date-time
   */
  completedAt: string;
  /** Outcomeid */
  outcomeId: number;
  /** Overallstatus */
  overallStatus: string;
}

/** OutcomeDataCreatedResponse */
export interface OutcomeDataCreatedResponse {
  /** Datasetid */
  datasetId: number;
  /** Outcomedataid */
  outcomeDataId: number;
  /** Simulationid */
  simulationId: number;
  /** Sourcetype */
  sourceType: string;
  /** Status */
  status: string;
}

/** OutcomeResultResponse */
export interface OutcomeResultResponse {
  /** Comparisonrows */
  comparisonRows: ComparisonRowResponse[];
  /**
   * Createdat
   * @format date-time
   */
  createdAt: string;
  /** Newbottlenecks */
  newBottlenecks: NewBottleneckResponse[];
  /** Outcomeid */
  outcomeId: number;
  /** Overallstatus */
  overallStatus: string;
  /** Reevaluation */
  reevaluation: ReevaluationResponse[];
  /** Simulationid */
  simulationId: number;
  /** Trends */
  trends: MetricTrendResponse[];
}

/** OutcomeSummaryResponse */
export interface OutcomeSummaryResponse {
  /** Cashafterrepaymentstatus */
  cashAfterRepaymentStatus: string;
  /** Onlineratiostatus */
  onlineRatioStatus: string;
  /** Salesgrowthstatus */
  salesGrowthStatus: string;
}

/** PlanSummaryResponse */
export interface PlanSummaryResponse {
  /** Plancode */
  planCode: string;
  /** Title */
  title: string;
}

/** ReasonResponse */
export interface ReasonResponse {
  /** Bottleneckid */
  bottleneckId: number | null;
  /** Category */
  category: string;
  /** Description */
  description: string;
  /** Sourcetype */
  sourceType: string;
}

/** ReevaluationResponse */
export interface ReevaluationResponse {
  /** Bottlenecktype */
  bottleneckType: string;
  /** Changetype */
  changeType: string;
  /** Detail */
  detail: string | null;
}

/** RepaymentTypeRequest */
export enum RepaymentTypeRequest {
  EQUAL_PAYMENT = "EQUAL_PAYMENT",
  EQUAL_PRINCIPAL = "EQUAL_PRINCIPAL",
  BULLET_PAYMENT = "BULLET_PAYMENT",
}

/** ScenarioComparisonResponse */
export interface ScenarioComparisonResponse {
  /** Allocations */
  allocations: AllocationResponse[];
  financialResult: FinancialResultResponse;
  /** Riskreasons */
  riskReasons: string[];
  /** Scenariocode */
  scenarioCode: string;
  /** Scenarioid */
  scenarioId: number;
  /** Strategytype */
  strategyType: string;
  /** Targetmetrics */
  targetMetrics: string[];
  /** Title */
  title: string;
}

/** ScenarioResponse */
export interface ScenarioResponse {
  /** Allocations */
  allocations: AllocationResponse[];
  financialResult: FinancialResultResponse;
  /** Reasons */
  reasons: ReasonResponse[];
  /** Riskreasons */
  riskReasons: string[];
  /** Scenariocode */
  scenarioCode: string;
  /** Scenarioid */
  scenarioId: number;
  /** Strategytype */
  strategyType: string;
  /** Targetmetrics */
  targetMetrics: string[];
  /** Title */
  title: string;
}

/** ScenarioSelectionRequest */
export interface ScenarioSelectionRequest {
  /**
   * Scenarioid
   * @exclusiveMin 0
   */
  scenarioId: number;
}

/** ScenarioSelectionResponse */
export interface ScenarioSelectionResponse {
  /** Locked */
  locked: boolean;
  /**
   * Selectedat
   * @format date-time
   */
  selectedAt: string;
  /** Selectedscenarioid */
  selectedScenarioId: number;
  /** Simulationid */
  simulationId: number;
}

/** SelectedPlanResponse */
export interface SelectedPlanResponse {
  /** Scenariocode */
  scenarioCode: string;
  /** Scenarioid */
  scenarioId: number;
  /** Title */
  title: string;
}

/** SimulationComparisonResponse */
export interface SimulationComparisonResponse {
  /** Disclaimer */
  disclaimer: string;
  /** Recommendationprovided */
  recommendationProvided: boolean;
  /** Scenarios */
  scenarios: ScenarioComparisonResponse[];
  /** Simulationid */
  simulationId: number;
}

/** SimulationCreatedResponse */
export interface SimulationCreatedResponse {
  /** Simulationid */
  simulationId: number;
  /** Status */
  status: string;
}

/** SimulationCreationRequest */
export interface SimulationCreationRequest {
  /** Annualinterestrate */
  annualInterestRate: number | string;
  /**
   * Diagnosisid
   * @exclusiveMin 0
   */
  diagnosisId: number;
  /**
   * Gracemonths
   * @min 0
   * @max 2147483647
   */
  graceMonths: number;
  /**
   * Loanamount
   * @exclusiveMin 0
   * @max 9223372036854776000
   */
  loanAmount: number;
  repaymentType: RepaymentTypeRequest;
  /**
   * Termmonths
   * @exclusiveMin 0
   * @max 2147483647
   */
  termMonths: number;
}

/** SimulationResponse */
export interface SimulationResponse {
  /** Businessid */
  businessId: number;
  /**
   * Createdat
   * @format date-time
   */
  createdAt: string;
  /** Diagnosisid */
  diagnosisId: number;
  loanCondition: LoanConditionResponse;
  /** Scenarios */
  scenarios: ScenarioResponse[];
  /** Selectedscenarioid */
  selectedScenarioId: number | null;
  /** Simulationid */
  simulationId: number;
  /** Status */
  status: string;
}

/** UnresolvedBottleneckResponse */
export interface UnresolvedBottleneckResponse {
  /** Bottlenecktype */
  bottleneckType: string;
  /** Changetype */
  changeType: string;
  /** Detail */
  detail: string | null;
}

/** ValidationError */
export interface ValidationError {
  /** Context */
  ctx?: object;
  /** Input */
  input?: any;
  /** Location */
  loc: (string | number)[];
  /** Message */
  msg: string;
  /** Error Type */
  type: string;
}

/** VerificationTargetResponse */
export interface VerificationTargetResponse {
  /** Businessname */
  businessName: string;
  /** Dayselapsed */
  daysElapsed: number;
  /** Executionregistered */
  executionRegistered: boolean;
  /** Loanamount */
  loanAmount: number;
  /** Plansummaries */
  planSummaries: PlanSummaryResponse[];
  /** Region */
  region: string;
  /**
   * Savedat
   * @format date-time
   */
  savedAt: string;
  /** Simulationid */
  simulationId: number;
}

/** VerificationTargetsResponse */
export interface VerificationTargetsResponse {
  /** Businessid */
  businessId: number;
  /** Targets */
  targets: VerificationTargetResponse[];
}
