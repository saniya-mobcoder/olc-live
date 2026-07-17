export type Requirement = {
  requirement_id: string;
  production_id: string;
  production_title: string;
  production_type: string;
  required_category: string;
  required_primary_role: string;
  acceptable_secondary_roles: string[];
  mandatory_skills: string[];
  preferred_skills: string[];
  city: string;
  country: string;
  latitude: number;
  longitude: number;
  venue_type: string;
  rehearsal_start_date: string;
  rehearsal_end_date: string;
  performance_start_date: string;
  performance_end_date: string;
  minimum_audition_score: number;
  weekly_budget_max_usd: number;
  visa_sponsorship_available: boolean;
  required_languages: string[];
  overnight_rehearsal_required: boolean;
  aquatic_experience_required: boolean;
  aerial_experience_required: boolean;
  stunt_experience_required: boolean;
  required_safety_certifications: string[];
  special_instructions: string;
};

export type Talent = {
  talent_id: string;
  full_name: string;
  profile_title: string;
  talent_category: string;
  primary_role: string;
  secondary_roles: string[];
  primary_skills: string[];
  secondary_skills: string[];
  city: string;
  country: string;
  latitude: number;
  longitude: number;
  languages: string[];
  physical_skill_level: string;
  aquatic_performance_experience: boolean;
  aerial_performance_experience: boolean;
  stunt_experience: boolean;
  weekly_contract_rate_usd: number;
  rehearsal_day_rate_usd: number;
  audition_readiness_score: number;
  average_director_rating: number | null;
  completed_productions: number;
  professional_certifications: string[];
  work_authorized_countries: string[];
};

export type MatchResult = {
  talent_id: string;
  talent: Talent | null;
  eligible: boolean;
  rank: number | null;
  score: number | null;
  match_category: string;
  breakdown: {
    factors?: Record<string, number>;
    weights?: Record<string, number>;
    via_secondary_role?: boolean;
    weighted_total?: number;
    feedback_prior?: number;
    ranking_mode?: string;
    hybrid_score?: number;
  };
  failed_gates: string[];
  positive_reasons: string[];
  risk_factors: string[];
  rejection_reasons: string[];
  distance_km: number | null;
};

export type MatchDecision = {
  id: number;
  run_id: string;
  talent_id: string;
  decision: "hire" | "hold" | "reject" | string;
  reason: string;
  created_at: string;
};

export type ScoreAgainst = {
  talent_id: string;
  requirement_id: string;
  eligible: boolean;
  score: number | null;
  match_category: string;
  failed_gates: string[];
  positive_reasons: string[];
  rejection_reasons: string[];
  risk_factors: string[];
  breakdown: Record<string, unknown>;
  distance_km: number | null;
};

export type MatchRun = {
  id: string;
  requirement_id: string;
  created_at: string;
  scenario_label: string;
  params_override: Record<string, unknown>;
  shortlist: MatchResult[];
  other_eligible: MatchResult[];
  rejected: MatchResult[];
  eligible_count: number;
  rejected_count: number;
};

export type WhatIfResult = {
  baseline: MatchRun;
  scenario: MatchRun;
  eligible_delta: number;
  new_talent_ids: string[];
  lost_talent_ids: string[];
};

export type AuditEvent = {
  id: number;
  run_id: string;
  talent_id: string | null;
  event_type: string;
  message: string;
  detail: Record<string, unknown>;
  created_at: string;
};

export type PoolAnalytics = {
  by_region: { region: string; count: number }[];
  by_role: { role: string; count: number }[];
  by_category: { category: string; count: number }[];
  gaps: Record<string, unknown>[];
  totals: Record<string, number>;
};

export type EdgeScenario = {
  id: string;
  name: string;
  requirement_id: string;
  talent_id?: string;
  params_override?: Record<string, unknown>;
};

export type ExecutiveReport = {
  id: string;
  period_start: string;
  period_end: string;
  created_at: string;
  scenario_label: string;
  payload: {
    period?: { start: string; end: string };
    operational?: {
      requirements_opened?: number;
      requirements_closed?: number;
      match_runs?: number;
      avg_eligible_per_run?: number;
      top5_fill_rate_pct?: number;
      avg_runs_per_requirement?: number;
      decision_count?: number;
      decision_acceptance_pct?: number;
      gate_fail_frequency?: { gate: string; count: number }[];
    };
    commercial?: {
      contract_value_usd?: number;
      credits_in_period?: number;
      rehire_eligible_share_pct?: number;
      avg_weekly_budget_max_usd?: number;
      avg_talent_weekly_rate_usd?: number;
      budget_vs_rate_delta_usd?: number;
    };
  };
};

export type StageLyncPerson = {
  stagelync_person_id: string;
  display_name: string;
  primary_role: string;
  secondary_roles: string[];
  skills: string[];
  city: string;
  country: string;
  latitude: number;
  longitude: number;
  languages: string[];
  weekly_rate_usd: number;
  experience_years: number;
  physical_skill_level: string;
  aquatic: boolean;
  aerial: boolean;
  stunt: boolean;
  certifications: string[];
  work_authorizations: string[];
  profile_summary: string;
  synced_at: string;
  link_status: string;
  talent_id: string | null;
};

export type Booking = {
  id: string;
  requirement_id: string;
  talent_id: string;
  match_run_id: string;
  decision_id: number | null;
  status: string;
  weekly_rate_usd: number;
  start_date: string;
  end_date: string;
  created_at: string;
  production_title?: string | null;
  talent_name?: string | null;
};

export type MarketingDraft = {
  id: string;
  channel: string;
  body: string;
  source_ref: string;
  created_at: string;
};
