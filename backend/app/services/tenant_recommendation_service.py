"""
Tenant Recommendation Service - AI-powered tenant mix optimization

Recommends optimal tenants for vacant spaces based on:
1. Current tenant mix (gap analysis)
2. Demographics (Census data)
3. Market trends
4. Synergy with existing tenants
5. Revenue potential
"""
from typing import Dict, List, Optional
from datetime import date
from sqlalchemy.orm import Session
import logging
from collections import Counter

from app.models.property import Property
from app.models.tenant_recommendation import TenantRecommendation
from app.models.rent_roll_data import RentRollData
from app.services.property_research_service import PropertyResearchService

logger = logging.getLogger(__name__)


class TenantRecommendationService:
    """
    AI-powered tenant recommendation system

    Uses multi-factor analysis to suggest optimal tenants for vacant spaces
    """

    # Comprehensive tenant categories with examples
    TENANT_CATEGORIES = {
        "grocery_anchor": {
            "name": "Grocery Anchor",
            "examples": ["Whole Foods", "Trader Joe's", "Kroger", "Publix", "Sprouts"],
            "typical_sqft": 40000,
            "revenue_multiple": 1.5,
            "foot_traffic_score": 10
        },
        "fast_food": {
            "name": "Fast Food",
            "examples": ["Chipotle", "Panera", "Chick-fil-A", "Shake Shack", "Five Guys"],
            "typical_sqft": 2500,
            "revenue_multiple": 1.2,
            "foot_traffic_score": 8
        },
        "casual_dining": {
            "name": "Casual Dining",
            "examples": ["Olive Garden", "Red Lobster", "Texas Roadhouse", "Cheesecake Factory"],
            "typical_sqft": 5000,
            "revenue_multiple": 1.1,
            "foot_traffic_score": 6
        },
        "fast_casual": {
            "name": "Fast Casual",
            "examples": ["Sweetgreen", "Cava", "Blaze Pizza", "Mod Pizza"],
            "typical_sqft": 2000,
            "revenue_multiple": 1.3,
            "foot_traffic_score": 7
        },
        "coffee_shop": {
            "name": "Coffee Shop",
            "examples": ["Starbucks", "Peet's Coffee", "Dunkin'", "Local Roasters"],
            "typical_sqft": 1500,
            "revenue_multiple": 1.2,
            "foot_traffic_score": 9
        },
        "fitness": {
            "name": "Fitness Center",
            "examples": ["Planet Fitness", "Orangetheory", "LA Fitness", "CorePower Yoga"],
            "typical_sqft": 8000,
            "revenue_multiple": 1.0,
            "foot_traffic_score": 7
        },
        "healthcare": {
            "name": "Healthcare Services",
            "examples": ["Urgent Care", "Dentist", "Pharmacy", "Medical Clinic"],
            "typical_sqft": 3000,
            "revenue_multiple": 1.1,
            "foot_traffic_score": 5
        },
        "banking": {
            "name": "Banking/Financial",
            "examples": ["Bank Branch", "Credit Union", "Financial Advisor"],
            "typical_sqft": 2500,
            "revenue_multiple": 0.9,
            "foot_traffic_score": 4
        },
        "personal_services": {
            "name": "Personal Services",
            "examples": ["Dry Cleaning", "Salon", "Nail Spa", "Barber"],
            "typical_sqft": 1200,
            "revenue_multiple": 1.0,
            "foot_traffic_score": 6
        },
        "retail_apparel": {
            "name": "Retail Apparel",
            "examples": ["Gap", "Old Navy", "TJ Maxx", "Ross", "H&M"],
            "typical_sqft": 6000,
            "revenue_multiple": 1.1,
            "foot_traffic_score": 7
        },
        "specialty_retail": {
            "name": "Specialty Retail",
            "examples": ["Pet Store", "Hobby Lobby", "GameStop", "Books-A-Million"],
            "typical_sqft": 4000,
            "revenue_multiple": 1.0,
            "foot_traffic_score": 5
        },
        "entertainment": {
            "name": "Entertainment",
            "examples": ["Movie Theater", "Bowling", "Arcade", "Escape Room"],
            "typical_sqft": 15000,
            "revenue_multiple": 1.2,
            "foot_traffic_score": 8
        },
        "kids_family": {
            "name": "Kids & Family",
            "examples": ["Daycare", "Kids Clothing", "Tutoring Center", "Kids Activities"],
            "typical_sqft": 3000,
            "revenue_multiple": 1.1,
            "foot_traffic_score": 6
        },
        "home_improvement": {
            "name": "Home Improvement",
            "examples": ["Home Depot", "Lowe's", "Ace Hardware", "Furniture Store"],
            "typical_sqft": 8000,
            "revenue_multiple": 1.0,
            "foot_traffic_score": 5
        },
        "luxury_retail": {
            "name": "Luxury Retail",
            "examples": ["Apple Store", "Lululemon", "Tesla Showroom", "Designer Boutique"],
            "typical_sqft": 3500,
            "revenue_multiple": 1.4,
            "foot_traffic_score": 6
        }
    }

    # Demographic preferences mapping
    DEMOGRAPHIC_PREFERENCES = {
        "high_income": ["grocery_anchor", "luxury_retail", "fitness", "casual_dining", "healthcare"],
        "medium_income": ["fast_food", "retail_apparel", "personal_services", "banking", "coffee_shop"],
        "low_income": ["fast_food", "specialty_retail", "personal_services"],
        "family_oriented": ["kids_family", "grocery_anchor", "casual_dining", "healthcare", "home_improvement"],
        "young_professional": ["fast_casual", "fitness", "coffee_shop", "personal_services", "luxury_retail"],
        "seniors": ["healthcare", "banking", "casual_dining", "grocery_anchor"],
        "students": ["fast_food", "coffee_shop", "fitness", "entertainment"]
    }

    # Synergy matrix - which categories work well together
    SYNERGY_PAIRS = {
        "grocery_anchor": ["fast_food", "coffee_shop", "banking", "personal_services", "pharmacy"],
        "fast_food": ["grocery_anchor", "retail_apparel", "entertainment"],
        "fitness": ["fast_casual", "coffee_shop", "healthcare", "personal_services"],
        "retail_apparel": ["fast_food", "coffee_shop", "personal_services"],
        "healthcare": ["pharmacy", "fitness", "personal_services"],
        "kids_family": ["fast_food", "grocery_anchor", "healthcare"]
    }

    def __init__(self, db: Session):
        self.db = db
        self.research_service = PropertyResearchService(db)

    def recommend_tenants(
        self,
        property_id: int,
        unit_identifier: Optional[str] = None,
        space_sqft: Optional[int] = None,
        top_n: int = 10
    ) -> Dict:
        """
        Generate tenant recommendations for a vacant space

        Args:
            property_id: Property ID
            unit_identifier: Specific unit/space (optional)
            space_sqft: Size of space in square feet (optional)
            top_n: Number of recommendations to return

        Returns:
            dict: Recommendations with scores and justifications
        """
        logger.info(f"Generating tenant recommendations for property {property_id}")

        try:
            # 1. Get property
            property = self.db.query(Property).filter(Property.id == property_id).first()
            if not property:
                return {"success": False, "error": "Property not found"}

            # 2. Analyze current tenant mix
            current_tenants = self._get_current_tenants(property_id)
            tenant_categories = self._categorize_tenants(current_tenants)

            # 3. Get demographics
            demographics = self.research_service.get_demographics(property_id)
            if not demographics:
                demographics = {}  # Use empty dict, algorithm will handle

            # 4. Get market data
            market_data = self.research_service.get_market_analysis(property_id)
            if not market_data:
                market_data = {}

            # 5. Identify gaps
            gaps = self._identify_tenant_gaps(tenant_categories, demographics)

            # 6. Generate recommendations
            recommendations = []
            for gap in gaps:
                category = gap['category']
                category_info = self.TENANT_CATEGORIES.get(category, {})

                # Calculate scores
                demographic_match = self._calculate_demographic_match(category, demographics)
                synergy_score = self._calculate_synergy(category, tenant_categories)
                market_demand = self._calculate_market_demand(category, market_data, demographics)
                revenue_potential = self._estimate_revenue(category, space_sqft, market_data)

                # Overall success probability (weighted average)
                success_probability = (
                    demographic_match * 0.30 +
                    synergy_score * 0.30 +
                    market_demand * 0.20 +
                    revenue_potential * 0.20
                )

                recommendation = {
                    "tenant_type": category_info.get('name', category),
                    "category_key": category,
                    "specific_examples": category_info.get('examples', [])[:5],
                    "demographic_match_score": round(demographic_match, 3),
                    "synergy_score": round(synergy_score, 3),
                    "market_demand_score": round(market_demand, 3),
                    "revenue_potential_score": round(revenue_potential, 3),
                    "success_probability": round(success_probability, 3),
                    "justification": self._generate_justification(
                        category, demographics, tenant_categories, market_data
                    ),
                    "typical_sqft": category_info.get('typical_sqft'),
                    "estimated_monthly_rent": self._estimate_monthly_rent(
                        category, space_sqft, market_data
                    ),
                    "foot_traffic_impact": category_info.get('foot_traffic_score', 5)
                }

                recommendations.append(recommendation)

            # 7. Sort by success probability
            recommendations.sort(key=lambda x: x['success_probability'], reverse=True)

            # 8. Take top N
            top_recommendations = recommendations[:top_n]

            # 9. Store in database
            tenant_rec = TenantRecommendation(
                property_id=property_id,
                unit_identifier=unit_identifier,
                space_sqft=space_sqft,
                recommendation_date=date.today(),
                recommendations=top_recommendations,
                demographics_used=demographics,
                tenant_mix_used=tenant_categories
            )
            self.db.add(tenant_rec)
            self.db.commit()
            self.db.refresh(tenant_rec)

            logger.info(f"Generated {len(top_recommendations)} recommendations")

            return {
                "success": True,
                "recommendations": top_recommendations,
                "current_tenant_mix": tenant_categories,
                "demographics": demographics,
                "recommendation_id": tenant_rec.id
            }

        except Exception as e:
            logger.error(f"Recommendation failed: {str(e)}")
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def analyze_tenant_mix(self, property_id: int) -> Dict:
        """
        Analyze current tenant mix and identify opportunities

        Returns:
            dict: Analysis with gaps, strengths, recommendations
        """
        current_tenants = self._get_current_tenants(property_id)
        tenant_categories = self._categorize_tenants(current_tenants)

        # Calculate mix metrics
        total_tenants = len(current_tenants)
        category_distribution = {
            cat: count / total_tenants if total_tenants > 0 else 0
            for cat, count in tenant_categories.items()
        }

        # Identify strengths and weaknesses
        strengths = []
        weaknesses = []

        if tenant_categories.get('grocery_anchor', 0) > 0:
            strengths.append("Strong anchor tenant (grocery) drives foot traffic")

        if len(tenant_categories) < 5:
            weaknesses.append("Limited tenant diversity - consider adding more categories")

        if tenant_categories.get('fast_food', 0) > 3:
            weaknesses.append("High concentration of fast food - consider diversification")

        return {
            "success": True,
            "total_tenants": total_tenants,
            "category_distribution": category_distribution,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "diversity_score": len(tenant_categories) / len(self.TENANT_CATEGORIES)
        }

    def calculate_tenant_synergy(
        self,
        property_id: int,
        proposed_tenant_category: str
    ) -> Dict:
        """
        Calculate synergy score for a proposed tenant

        Args:
            property_id: Property ID
            proposed_tenant_category: Category key (e.g., 'fast_food')

        Returns:
            dict: Synergy analysis
        """
        current_tenants = self._get_current_tenants(property_id)
        tenant_categories = self._categorize_tenants(current_tenants)

        synergy_score = self._calculate_synergy(proposed_tenant_category, tenant_categories)

        # Find synergistic categories already present
        synergistic_with = []
        synergy_pairs = self.SYNERGY_PAIRS.get(proposed_tenant_category, [])
        for category in synergy_pairs:
            if category in tenant_categories:
                synergistic_with.append(self.TENANT_CATEGORIES.get(category, {}).get('name', category))

        return {
            "success": True,
            "synergy_score": round(synergy_score, 3),
            "synergistic_with": synergistic_with,
            "explanation": self._generate_synergy_explanation(
                proposed_tenant_category, synergistic_with
            )
        }

    # Helper methods

    def _get_current_tenants(self, property_id: int) -> List[Dict]:
        """Get current tenants from rent roll"""
        tenants = self.db.query(RentRollData)\
            .filter(RentRollData.property_id == property_id)\
            .filter(RentRollData.tenant_name.isnot(None))\
            .all()

        return [
            {
                "name": t.tenant_name,
                "space_sqft": t.square_footage,
                "monthly_rent": t.monthly_rent
            }
            for t in tenants
        ]

    def _categorize_tenants(self, tenants: List[Dict]) -> Dict[str, int]:
        """Categorize tenants into types"""
        categories = Counter()

        for tenant in tenants:
            name = tenant['name'].lower()

            # Simple keyword matching (could be enhanced with ML)
            if any(word in name for word in ['grocery', 'market', 'food']):
                categories['grocery_anchor'] += 1
            elif any(word in name for word in ['chipotle', 'panera', 'chick', 'burger', 'pizza']):
                categories['fast_food'] += 1
            elif any(word in name for word in ['restaurant', 'grill', 'cafe']):
                categories['casual_dining'] += 1
            elif any(word in name for word in ['starbucks', 'coffee', 'dunkin']):
                categories['coffee_shop'] += 1
            elif any(word in name for word in ['gym', 'fitness', 'yoga']):
                categories['fitness'] += 1
            elif any(word in name for word in ['clinic', 'medical', 'dental', 'pharmacy']):
                categories['healthcare'] += 1
            elif any(word in name for word in ['bank', 'credit union']):
                categories['banking'] += 1
            elif any(word in name for word in ['salon', 'spa', 'barber', 'nails']):
                categories['personal_services'] += 1
            elif any(word in name for word in ['gap', 'clothing', 'apparel', 'fashion']):
                categories['retail_apparel'] += 1
            else:
                categories['specialty_retail'] += 1

        return dict(categories)

    def _identify_tenant_gaps(self, current_categories: Dict, demographics: Dict) -> List[Dict]:
        """Identify missing tenant categories that would work well"""
        gaps = []

        for category_key, category_info in self.TENANT_CATEGORIES.items():
            # Skip if category already well-represented
            if current_categories.get(category_key, 0) >= 2:
                continue

            # Calculate gap score
            gap_score = 1.0 - (current_categories.get(category_key, 0) / 3.0)  # Diminishing returns

            gaps.append({
                "category": category_key,
                "gap_score": gap_score,
                "current_count": current_categories.get(category_key, 0)
            })

        return gaps

    def _calculate_demographic_match(self, category: str, demographics: Dict) -> float:
        """Calculate how well category matches demographics"""
        if not demographics:
            return 0.5  # Neutral score

        score = 0.5  # Base score

        median_income = demographics.get('median_income', 50000)
        education = demographics.get('education_level', {})
        bachelors_rate = education.get('bachelors', 0.3)

        # Income-based matching
        if median_income >= 100000:
            demographic_profile = "high_income"
        elif median_income >= 60000:
            demographic_profile = "medium_income"
        else:
            demographic_profile = "low_income"

        if category in self.DEMOGRAPHIC_PREFERENCES.get(demographic_profile, []):
            score += 0.3

        # Education-based matching
        if bachelors_rate >= 0.4 and category in ['luxury_retail', 'fitness', 'fast_casual']:
            score += 0.2

        return min(1.0, score)

    def _calculate_synergy(self, category: str, existing_categories: Dict) -> float:
        """Calculate synergy with existing tenants"""
        if not existing_categories:
            return 0.5

        synergy_pairs = self.SYNERGY_PAIRS.get(category, [])
        synergy_count = sum(1 for cat in synergy_pairs if cat in existing_categories)

        # Score based on number of synergistic tenants
        if synergy_count >= 3:
            return 1.0
        elif synergy_count >= 2:
            return 0.8
        elif synergy_count >= 1:
            return 0.6
        else:
            return 0.4

    def _calculate_market_demand(self, category: str, market_data: Dict, demographics: Dict) -> float:
        """Calculate market demand for category"""
        score = 0.5  # Base

        if not market_data:
            return score

        # Rental rate trend
        rental_trend = market_data.get('rental_rate_trend', 'stable')
        if rental_trend == 'increasing':
            score += 0.3
        elif rental_trend == 'stable':
            score += 0.1

        # Vacancy rate (lower is better)
        vacancy = market_data.get('vacancy_rate', 0.1)
        if vacancy < 0.05:
            score += 0.2
        elif vacancy < 0.10:
            score += 0.1

        return min(1.0, score)

    def _estimate_revenue(self, category: str, space_sqft: Optional[int], market_data: Dict) -> float:
        """Estimate revenue potential (normalized 0-1)"""
        category_info = self.TENANT_CATEGORIES.get(category, {})
        revenue_multiple = category_info.get('revenue_multiple', 1.0)

        # Normalize to 0-1 scale (1.5x = 1.0, 0.9x = 0.6)
        score = (revenue_multiple - 0.9) / 0.6

        return max(0.0, min(1.0, score))

    def _estimate_monthly_rent(
        self,
        category: str,
        space_sqft: Optional[int],
        market_data: Dict
    ) -> Optional[float]:
        """Estimate monthly rent for space"""
        if not space_sqft:
            return None

        # Get market average rate per sqft (or use default)
        avg_rate_psf = market_data.get('avg_rental_rate_psf', 25.0) if market_data else 25.0

        # Apply category multiplier
        category_info = self.TENANT_CATEGORIES.get(category, {})
        revenue_multiple = category_info.get('revenue_multiple', 1.0)

        estimated_rate = avg_rate_psf * revenue_multiple
        monthly_rent = estimated_rate * space_sqft

        return round(monthly_rent, 2)

    def _generate_justification(
        self,
        category: str,
        demographics: Dict,
        tenant_categories: Dict,
        market_data: Dict
    ) -> str:
        """Generate human-readable justification"""
        category_info = self.TENANT_CATEGORIES.get(category, {})
        category_name = category_info.get('name', category)

        reasons = []

        # Demographics reason
        if demographics:
            median_income = demographics.get('median_income', 0)
            if median_income >= 100000 and category in self.DEMOGRAPHIC_PREFERENCES.get('high_income', []):
                reasons.append(f"High median income (${median_income:,}) aligns well with {category_name}")
            elif median_income >= 60000:
                reasons.append(f"Median income (${median_income:,}) supports {category_name}")

        # Synergy reason
        synergy_pairs = self.SYNERGY_PAIRS.get(category, [])
        synergistic_present = [cat for cat in synergy_pairs if cat in tenant_categories]
        if synergistic_present:
            reasons.append(f"Creates synergy with existing {', '.join(synergistic_present)} tenants")

        # Market reason
        if market_data:
            if market_data.get('rental_rate_trend') == 'increasing':
                reasons.append("Market rental rates are increasing")

        if not reasons:
            reasons.append(f"{category_name} represents a gap in current tenant mix")

        return ". ".join(reasons) + "."

    def _generate_synergy_explanation(self, category: str, synergistic_with: List[str]) -> str:
        """Generate synergy explanation"""
        if not synergistic_with:
            return "Limited synergy with current tenant mix"

        return f"Strong synergy with {', '.join(synergistic_with)}. These tenants complement each other and can drive cross-shopping."
