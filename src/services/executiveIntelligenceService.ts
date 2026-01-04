/**
 * Executive Intelligence Service (Frontend)
 *
 * Calculates executive-level metrics and investment recommendations from market intelligence data.
 * Provides actionable insights for C-level decision making.
 */

export interface ExecutiveSummary {
  locationScore: number | null;
  marketCapRate: number;
  rentGrowth: number | null;
  riskScore: number;
  opportunityScore: number;
  investmentRecommendation: InvestmentRecommendation;
  keyFindings: string[];
  executiveSummary: {
    headline: string;
    quickStats: {
      locationQuality: string;
      growthPotential: string;
      riskLevel: string;
      opportunityLevel: string;
    };
  };
}

export interface InvestmentRecommendation {
  action: 'BUY' | 'HOLD' | 'SELL' | 'REVIEW';
  confidence: number;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  rationale: string[];
  metrics: {
    netScore: number;
    capRatePremium: number;
  };
}

/**
 * Calculate location quality score (0-10)
 */
export function calculateLocationScore(
  locationIntel: any,
  demographics: any
): number | null {
  if (!locationIntel?.data) return null;

  try {
    const loc = locationIntel.data;
    let score = 0;

    // Mobility scores (30% weight)
    score += (loc.walk_score || 0) / 100 * 1.2;
    score += (loc.bike_score || 0) / 100 * 0.9;
    score += (loc.transit_score || 0) / 100 * 0.9;

    // Schools (20% weight)
    score += (loc.school_rating_avg || 5) / 10 * 2.0;

    // Safety (20% weight) - inverted (lower crime = higher score)
    score += (100 - (loc.crime_index || 50)) / 100 * 2.0;

    // Amenities (15% weight)
    const amenities = loc.amenities || {};
    let amenityScore = 0;
    if ((amenities.grocery_stores_1mi || 0) > 0) amenityScore += 0.4;
    if ((amenities.restaurants_1mi || 0) > 3) amenityScore += 0.3;
    if ((amenities.parks_1mi || 0) > 0) amenityScore += 0.3;
    if ((amenities.schools_2mi || 0) > 0) amenityScore += 0.3;
    if ((amenities.hospitals_5mi || 0) > 0) amenityScore += 0.2;
    score += Math.min(amenityScore, 1.5);

    // Demographics boost (15% weight)
    if (demographics?.data) {
      const demo = demographics.data;
      const income = demo.median_household_income || 0;
      const education = demo.college_educated_pct || 0;

      if (income > 80000) score += 0.8;
      else if (income > 60000) score += 0.6;
      else if (income > 40000) score += 0.4;

      if (education > 40) score += 0.7;
      else if (education > 25) score += 0.5;
      else if (education > 15) score += 0.3;
    }

    return Math.round(Math.min(score, 10) * 10) / 10;
  } catch (error) {
    console.error('Error calculating location score:', error);
    return null;
  }
}

/**
 * Calculate market cap rate from competitive analysis
 */
export function calculateMarketCapRate(competitiveAnalysis: any): number {
  if (!competitiveAnalysis?.data) return 0;
  return competitiveAnalysis.data.market_avg_cap_rate || 0;
}

/**
 * Extract rent growth forecast
 */
export function calculateRentGrowth(forecasts: any): number | null {
  if (!forecasts?.data) return null;
  const growth = forecasts.data.rent_growth_3yr_cagr;
  return growth !== null && growth !== undefined ? Math.round(growth * 10) / 10 : null;
}

/**
 * Calculate risk score (0-100, higher = more risk)
 */
export function calculateRiskScore(
  esgAssessment: any,
  economicIndicators: any,
  forecasts: any,
  locationIntel: any
): number {
  let risk = 0;

  try {
    // ESG Risks (30 points max)
    if (esgAssessment?.data) {
      const esgScore = esgAssessment.data.composite_score?.overall?.score || 75;
      risk += (100 - esgScore) / 100 * 30;
    } else {
      risk += 15; // Moderate risk if no ESG data
    }

    // Economic Conditions (25 points max)
    if (economicIndicators?.data) {
      const econ = economicIndicators.data;

      // Recession probability
      const recessionProb = econ.recession_probability?.value || 0;
      risk += (recessionProb / 100) * 10;

      // Unemployment
      const unemployment = econ.unemployment_rate?.value || 4;
      if (unemployment > 6) risk += 8;
      else if (unemployment > 5) risk += 5;
      else if (unemployment > 4) risk += 2;

      // Mortgage rates
      const mortgageRate = econ.mortgage_rate_30y?.value || 6;
      if (mortgageRate > 7) risk += 7;
      else if (mortgageRate > 6) risk += 4;
    } else {
      risk += 12; // Moderate risk if no economic data
    }

    // Market Forecast Risks (25 points max)
    if (forecasts?.data) {
      const rentGrowth = forecasts.data.rent_growth_3yr_cagr || 0;
      if (rentGrowth < 0) risk += 15;
      else if (rentGrowth < 2) risk += 10;
      else if (rentGrowth < 3) risk += 5;

      const vacancyForecast = forecasts.data.vacancy_rate_forecast || 5;
      if (vacancyForecast > 10) risk += 10;
      else if (vacancyForecast > 7) risk += 5;
    } else {
      risk += 12; // Moderate risk if no forecast
    }

    // Location/Crime (20 points max)
    if (locationIntel?.data) {
      const crimeIndex = locationIntel.data.crime_index || 50;
      risk += (crimeIndex / 100) * 20;
    } else {
      risk += 10; // Moderate risk if no location data
    }

    return Math.round(Math.min(risk, 100));
  } catch (error) {
    console.error('Error calculating risk score:', error);
    return 50; // Default moderate risk
  }
}

/**
 * Calculate opportunity score (0-100, higher = better)
 */
export function calculateOpportunityScore(
  locationScore: number | null,
  rentGrowth: number | null,
  demographics: any,
  competitiveAnalysis: any
): number {
  let score = 0;

  try {
    // Rent Growth Potential (30 points)
    if (rentGrowth !== null) {
      if (rentGrowth >= 5) score += 30;
      else if (rentGrowth >= 3) score += 20;
      else if (rentGrowth >= 2) score += 15;
      else if (rentGrowth >= 0) score += 10;
    } else {
      score += 15; // Moderate if unknown
    }

    // Location Quality (25 points)
    if (locationScore !== null) {
      score += (locationScore / 10) * 25;
    } else {
      score += 12; // Moderate if unknown
    }

    // Demographics (25 points)
    if (demographics?.data) {
      const demo = demographics.data;
      const income = demo.median_household_income || 0;
      const education = demo.college_educated_pct || 0;
      const population = demo.population || 0;

      if (income > 80000) score += 12;
      else if (income > 60000) score += 8;
      else if (income > 40000) score += 5;

      if (education > 40) score += 10;
      else if (education > 25) score += 6;
      else if (education > 15) score += 3;

      if (population > 5000) score += 3;
    } else {
      score += 12; // Moderate if unknown
    }

    // Competitive Positioning (20 points)
    if (competitiveAnalysis?.data) {
      const comp = competitiveAnalysis.data;
      const absorption = comp.absorption_rate_units_per_mo || 0;
      const newSupply = comp.new_supply_pipeline_units || 0;

      if (absorption > 0) {
        const monthsOfSupply = newSupply / Math.max(absorption, 1);
        if (monthsOfSupply < 12) score += 15; // Less than 1 year = strong opportunity
        else if (monthsOfSupply < 24) score += 10;
        else score += 5;
      }

      score += 5; // Additional competitive positioning points
    } else {
      score += 10; // Moderate if unknown
    }

    return Math.round(Math.min(score, 100));
  } catch (error) {
    console.error('Error calculating opportunity score:', error);
    return 50; // Default moderate
  }
}

/**
 * Generate investment recommendation
 */
export function generateInvestmentRecommendation(
  riskScore: number,
  opportunityScore: number,
  yourCapRate: number,
  marketCapRate: number
): InvestmentRecommendation {
  const netScore = opportunityScore - riskScore;
  const capPremium = marketCapRate > 0 ? yourCapRate - marketCapRate : 0;

  let action: 'BUY' | 'HOLD' | 'SELL' | 'REVIEW' = 'REVIEW';
  let confidence = 50;
  let priority: 'HIGH' | 'MEDIUM' | 'LOW' = 'MEDIUM';
  const rationale: string[] = [];

  // Strong Buy
  if (netScore >= 30 && opportunityScore >= 70) {
    action = 'BUY';
    confidence = 85;
    priority = 'HIGH';
    rationale.push(`Exceptional opportunity (${opportunityScore}/100)`);
    rationale.push(`Risk is manageable (${riskScore}/100)`);
  }
  // Moderate Buy
  else if (netScore >= 15 && opportunityScore >= 60) {
    action = 'BUY';
    confidence = 70;
    priority = 'MEDIUM';
    rationale.push(`Strong opportunity (${opportunityScore}/100)`);
    rationale.push(`Acceptable risk level (${riskScore}/100)`);
  }
  // Hold - performing well
  else if (netScore >= 0 && capPremium >= 0) {
    action = 'HOLD';
    confidence = 75;
    priority = 'LOW';
    rationale.push(`Asset performing at/above market (${capPremium >= 0 ? '+' : ''}${capPremium.toFixed(1)}% cap rate)`);
    rationale.push('Balanced opportunity/risk profile');
  }
  // Hold - neutral
  else if (netScore >= -15) {
    action = 'HOLD';
    confidence = 60;
    priority = 'MEDIUM';
    rationale.push('Market conditions stable');
    rationale.push('Monitor for changes in risk/opportunity balance');
  }
  // Sell - high risk
  else if (riskScore >= 70) {
    action = 'SELL';
    confidence = 80;
    priority = 'HIGH';
    rationale.push(`High risk exposure (${riskScore}/100)`);
    rationale.push(`Limited upside potential (${opportunityScore}/100)`);
  }
  // Sell - underperforming
  else if (capPremium < -1.0 && opportunityScore < 40) {
    action = 'SELL';
    confidence = 75;
    priority = 'HIGH';
    rationale.push(`Underperforming market (${capPremium.toFixed(1)}% cap rate)`);
    rationale.push('Weak growth prospects');
  }
  // Review
  else {
    action = 'REVIEW';
    confidence = 50;
    priority = 'MEDIUM';
    rationale.push('Mixed signals - detailed analysis recommended');
    rationale.push(`Opportunity: ${opportunityScore}/100, Risk: ${riskScore}/100`);
  }

  // Add cap rate context if available
  if (marketCapRate > 0 && !rationale.some(r => r.includes('cap rate'))) {
    if (capPremium >= 0.5) {
      rationale.push(`Outperforming market by ${capPremium.toFixed(1)}%`);
    } else if (capPremium <= -0.5) {
      rationale.push(`Underperforming market by ${Math.abs(capPremium).toFixed(1)}%`);
    }
  }

  return {
    action,
    confidence,
    priority,
    rationale,
    metrics: {
      netScore,
      capRatePremium: Math.round(capPremium * 100) / 100
    }
  };
}

/**
 * Generate complete executive summary
 */
export function generateExecutiveSummary(
  marketIntelligence: any,
  yourCapRate: number = 0
): ExecutiveSummary {
  try {
    const { demographics, location_intelligence, esg_assessment, forecasts, competitive_analysis, ai_insights } = marketIntelligence;

    // Calculate all metrics
    const locationScore = calculateLocationScore(location_intelligence, demographics);
    const marketCapRate = calculateMarketCapRate(competitive_analysis);
    const rentGrowth = calculateRentGrowth(forecasts);
    const riskScore = calculateRiskScore(esg_assessment, marketIntelligence.economic_indicators, forecasts, location_intelligence);
    const opportunityScore = calculateOpportunityScore(locationScore, rentGrowth, demographics, competitive_analysis);
    const investmentRecommendation = generateInvestmentRecommendation(riskScore, opportunityScore, yourCapRate, marketCapRate);
    const safeLocationScore = locationScore ?? 0;
    const safeRentGrowth = rentGrowth ?? 0;

    // Extract key findings
    const keyFindings: string[] = [];
    if (ai_insights?.data) {
      const opportunities = ai_insights.data.opportunities || [];
      keyFindings.push(...opportunities.slice(0, 2));
    }

    // Generate headline
    const { action, rationale } = investmentRecommendation;
    let headline = `${action}: ${rationale[0] || 'Evaluation needed'}`;
    if (action === 'BUY' && investmentRecommendation.confidence >= 80 && locationScore !== null) {
      headline = `STRONG BUY: Premium location (${safeLocationScore}/10) with ${safeRentGrowth}% growth potential`;
    }

    return {
      locationScore,
      marketCapRate,
      rentGrowth,
      riskScore,
      opportunityScore,
      investmentRecommendation,
      keyFindings,
      executiveSummary: {
        headline,
        quickStats: {
          locationQuality: safeLocationScore >= 8 ? 'Premium' : safeLocationScore >= 6 ? 'Strong' : safeLocationScore >= 4 ? 'Average' : 'Below Average',
          growthPotential: safeRentGrowth >= 5 ? 'Exceptional' : safeRentGrowth >= 3 ? 'Strong' : safeRentGrowth >= 2 ? 'Moderate' : safeRentGrowth >= 0 ? 'Stable' : 'Declining',
          riskLevel: riskScore >= 70 ? 'High Risk' : riskScore >= 50 ? 'Moderate Risk' : riskScore >= 30 ? 'Low Risk' : 'Minimal Risk',
          opportunityLevel: opportunityScore >= 75 ? 'Exceptional' : opportunityScore >= 60 ? 'Strong' : opportunityScore >= 40 ? 'Moderate' : 'Limited'
        }
      }
    };
  } catch (error) {
    console.error('Error generating executive summary:', error);
    return {
      locationScore: null,
      marketCapRate: 0,
      rentGrowth: null,
      riskScore: 50,
      opportunityScore: 50,
      investmentRecommendation: {
        action: 'REVIEW',
        confidence: 0,
        priority: 'HIGH',
        rationale: ['Error calculating recommendation - manual review required'],
        metrics: { netScore: 0, capRatePremium: 0 }
      },
      keyFindings: [],
      executiveSummary: {
        headline: 'Insufficient data for recommendation',
        quickStats: {
          locationQuality: 'Unknown',
          growthPotential: 'Unknown',
          riskLevel: 'Unknown',
          opportunityLevel: 'Unknown'
        }
      }
    };
  }
}
