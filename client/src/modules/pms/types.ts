export interface CoInventor {
  id: number;
  user_id: number;
  inventor_name: string;
  affiliation: string;
  contribution_percentage: string;
  agreement_signed: boolean;
  agreement_signed_at: string | null;
}

export interface PriorArtReference {
  id: number;
  title: string;
  citation_type: string;
  publication_number_or_doi: string;
  relevance_summary: string;
  attached_file_drive_link: string;
}

export interface InternalReview {
  id: number;
  reviewer_user_id: number;
  review_stage: string;
  verdict: string;
  comments: string;
  novelty_score: number;
  inventive_step_score: number;
  commercial_viability_score: number;
  created_at: string;
}

export interface PatentBudget {
  id: number;
  estimated_filing_fee: string;
  estimated_attorney_fee: string;
  estimated_search_fee: string;
  total_estimated_amount: string;
  approved_amount: string | null;
  budget_status: string;
  decided_by_user_id: number | null;
  decision_date: string | null;
  escalation_notes: string;
}

export interface PatentFinancialTransaction {
  id: number;
  transaction_type: string;
  amount: string;
  currency: string;
  payment_status: string;
  reference_no: string;
  recorded_by_user_id: number;
  effective_date: string;
  description: string;
  created_at: string;
}

export interface OfficeAction {
  id: number;
  action_type: string;
  issuing_authority: string;
  issue_date: string;
  statutory_deadline: string;
  objections_summary: string;
  response_draft: string;
  response_status: string;
  response_submitted_date: string | null;
  handled_by_attorney_id: number;
}

export interface MaintenanceRenewal {
  id: number;
  renewal_year: number;
  due_date: string;
  grace_period_deadline: string;
  annuity_fee: string;
  decision: string;
  decided_by_user_id: number | null;
  payment_reference: string;
}

export interface PatentApplication {
  id: number;
  application_no: string;
  title: string;
  abstract: string;
  detailed_description: string;
  claims: string;
  field_of_invention: string;
  applicant_user_id: number;
  status: string;
  filing_type: string;
  official_filing_number: string;
  official_filing_date: string | null;
  grant_number: string;
  grant_date: string | null;
  assigned_director_id: number | null;
  assigned_attorney_id: number | null;
  inventors: CoInventor[];
  prior_art_references: PriorArtReference[];
  budget: PatentBudget | null;
  created_at: string;
  updated_at: string;
}
