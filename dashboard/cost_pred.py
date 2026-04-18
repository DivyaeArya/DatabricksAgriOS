import requests
import json
from typing import Dict, Optional, List

class AgricultureFinancialEngine:
    def __init__(self, api_key: str, databricks_token: Optional[str] = None):
        self.api_key = "579b464db66ec23bdd0000017c1ba99d654048586811506b696819bc"
        self.resource_id = "9ef84268-d588-465a-a308-a864a43d0070"
        self.base_url = f"https://api.data.gov.in/resource/{self.resource_id}"
        self.databricks_token = "dapi579b464db66ec23bdd0000017c1ba99d654048586811506b696819bc"
        
        # Regional yield estimates (quintals per acre)
        self.crop_yields = {
            "wheat": 15.0,
            "rice": 18.0,
            "gram": 8.0,
            "soy": 10.0,
            "cotton": 12.0,
            "sugarcane": 300.0,
            "maize": 20.0,
            "default": 12.0
        }
        
        # Cost parameters (per acre in ₹)
        self.base_costs = {
            "land_preparation": 3500,
            "seeds_percentage": 0.08,
            "fertilizer_per_acre": 4500,
            "pesticide_per_acre": 2000,
            "irrigation_per_acre": 5000,
            "labor_per_acre": 8000,
            "equipment_rental": 2500,
            "miscellaneous": 1500
        }

    def get_available_crops(self, state: str, district: str) -> Dict:
        """Get list of all available crops in the mandi for a location."""
        params = {
            "api-key": self.api_key,
            "format": "json",
            "filters[state.keyword]": state,
            "filters[district]": district,
            "limit": 1000
        }
        try:
            res = requests.get(self.base_url, params=params, timeout=10).json()
            records = res.get('records', [])
            
            if not records:
                return {
                    "success": False,
                    "message": f"No mandi data available for {district}, {state}"
                }
            
            # Get unique crops with their prices
            crops_dict = {}
            for rec in records:
                crop_name = rec.get('commodity', '').strip()
                if crop_name and crop_name not in crops_dict:
                    crops_dict[crop_name] = {
                        "name": crop_name,
                        "market": rec.get('market', 'N/A'),
                        "modal_price": float(rec.get('modal_price', 0))
                    }
            
            # Sort by name
            crops_list = sorted(crops_dict.values(), key=lambda x: x['name'])
            
            return {
                "success": True,
                "state": state,
                "district": district,
                "crops": crops_list,
                "count": len(crops_list)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error fetching crops: {str(e)}"
            }

    def get_all_local_crops(self, state: str, district: str) -> Dict:
        """Fetches every unique crop name currently in the Mandi."""
        params = {
            "api-key": self.api_key,
            "format": "json",
            "filters[state.keyword]": state,
            "filters[district]": district,
            "limit": 1000
        }
        try:
            res = requests.get(self.base_url, params=params, timeout=10).json()
            records = res.get('records', [])
            return {rec['commodity']: rec for rec in records}
        except Exception as e:
            return {}

    def estimate_yield(self, crop_name: str) -> float:
        """Estimates yield based on crop type."""
        for crop_key, yield_val in self.crop_yields.items():
            if crop_key in crop_name.lower():
                return yield_val
        return self.crop_yields["default"]

    def calculate_costs(self, modal_price: float, acres: float, estimated_yield: float) -> Dict:
        """Calculate comprehensive farming costs."""
        expected_revenue = modal_price * estimated_yield * acres
        
        costs = {
            "land_preparation": self.base_costs["land_preparation"] * acres,
            "seeds": expected_revenue * self.base_costs["seeds_percentage"],
            "fertilizers": self.base_costs["fertilizer_per_acre"] * acres,
            "pesticides": self.base_costs["pesticide_per_acre"] * acres,
            "irrigation": self.base_costs["irrigation_per_acre"] * acres,
            "labor": self.base_costs["labor_per_acre"] * acres,
            "equipment": self.base_costs["equipment_rental"] * acres,
            "miscellaneous": self.base_costs["miscellaneous"] * acres
        }
        
        total_capex = sum(costs.values())
        
        return {
            "breakdown": costs,
            "total": round(total_capex, 2)
        }

    def assess_risk_with_llm(self, crop: str, state: str, district: str, 
                            modal_price: float, roi: float) -> Dict:
        """Use LLM to assess agricultural and financial risks."""
        if not self.databricks_token:
            return {
                "risk_level": "medium",
                "summary": "LLM risk assessment unavailable (no token provided)",
                "factors": []
            }
        
        prompt = f"""Analyze the agricultural and financial risk for the following farming scenario:

Crop: {crop}
Location: {district}, {state}
Current Market Price: ₹{modal_price}/Quintal
Projected ROI: {roi}%

Assess risks considering:
1. Market volatility and price fluctuations
2. Regional climate and weather patterns
3. Crop-specific diseases and pest risks
4. Input cost inflation
5. Water availability
6. Demand-supply dynamics

Provide a JSON response with:
- risk_level: "low", "medium", or "high"
- summary: Brief 2-sentence risk assessment
- factors: List of 3-5 key risk factors with severity (low/medium/high)

Response format:
{{
  "risk_level": "medium",
  "summary": "Risk assessment summary here",
  "factors": [
    {{"factor": "Market volatility", "severity": "medium", "description": "Price fluctuations expected"}},
    {{"factor": "Water stress", "severity": "high", "description": "Low rainfall predicted"}}
  ]
}}"""

        try:
            response = requests.post(
                "https://adb-8246969749179036.16.azuredatabricks.net/serving-endpoints/databricks-meta-llama-3-1-70b-instruct/invocations",
                headers={
                    "Authorization": f"Bearer {self.databricks_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "messages": [
                        {"role": "system", "content": "You are an agricultural risk assessment expert. Respond only with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.3
                },
                timeout=30
            )
            
            if response.status_code == 200:
                llm_response = response.json()
                content = llm_response.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                try:
                    risk_data = json.loads(content)
                    return risk_data
                except json.JSONDecodeError:
                    return {
                        "risk_level": "medium",
                        "summary": content[:200] if content else "Risk assessment completed",
                        "factors": []
                    }
            else:
                return {
                    "risk_level": "medium",
                    "summary": "LLM service temporarily unavailable",
                    "factors": []
                }
                
        except Exception as e:
            return {
                "risk_level": "medium",
                "summary": f"Risk assessment error: {str(e)[:100]}",
                "factors": []
            }

    def calculate_metrics(self, user_input: str, acres: float, state: str, district: str) -> Dict:
        """Calculate comprehensive financial metrics with realistic cost modeling."""
        # 1. Fetch current valid crop list
        available_crops = self.get_all_local_crops(state, district)
        
        if not available_crops:
            return {"error": f"Unable to fetch crop data for {district}, {state}"}
        
        # 2. Smart matching
        match = None
        user_input_low = user_input.lower()
        
        for official_name in available_crops:
            if user_input_low in official_name.lower():
                match = official_name
                break
        
        if not match:
            return {"error": f"Crop '{user_input}' not found in {district} today."}

        # 3. Extract price and estimate yield
        data = available_crops[match]
        modal_price = float(data['modal_price'])
        estimated_yield = self.estimate_yield(match)
        
        # 4. Calculate revenue
        total_revenue = modal_price * estimated_yield * acres
        
        # 5. Calculate comprehensive costs
        cost_analysis = self.calculate_costs(modal_price, acres, estimated_yield)
        total_capex = cost_analysis["total"]
        
        # 6. Calculate profit and ROI
        net_profit = total_revenue - total_capex
        roi_percentage = (net_profit / total_capex) * 100 if total_capex > 0 else 0
        
        # 7. Risk assessment via LLM
        risk_assessment = self.assess_risk_with_llm(
            match, state, district, modal_price, roi_percentage
        )
        
        return {
            "commodity": match,
            "location": {
                "state": state,
                "district": district,
                "mandi": data['market']
            },
            "market_data": {
                "price_per_quintal": f"₹{modal_price}",
                "estimated_yield_per_acre": f"{estimated_yield} quintals",
                "total_area": f"{acres} acres"
            },
            "financial_analysis": {
                "total_revenue": f"₹{round(total_revenue, 2):,.2f}",
                "cost_breakdown": {k: f"₹{round(v, 2):,.2f}" for k, v in cost_analysis["breakdown"].items()},
                "total_capex": f"₹{round(total_capex, 2):,.2f}",
                "net_profit": f"₹{round(net_profit, 2):,.2f}",
                "roi": f"{round(roi_percentage, 2)}%",
                "breakeven_price": f"₹{round(total_capex / (estimated_yield * acres), 2)}/Quintal"
            },
            "risk_assessment": risk_assessment,
            "recommendations": self._generate_recommendations(roi_percentage, risk_assessment)
        }
    
    def _generate_recommendations(self, roi: float, risk_data: Dict) -> list:
        """Generate actionable recommendations based on financial metrics."""
        recommendations = []
        
        if roi > 50:
            recommendations.append("Excellent ROI projection - consider maximizing acreage")
        elif roi > 25:
            recommendations.append("Good profit margins - proceed with planned cultivation")
        elif roi > 10:
            recommendations.append("Moderate returns - monitor input costs closely")
        else:
            recommendations.append("Low profitability - evaluate alternative crops or cost reduction strategies")
        
        risk_level = risk_data.get("risk_level", "medium")
        if risk_level == "high":
            recommendations.append("High risk detected - consider crop insurance and diversification")
        elif risk_level == "low":
            recommendations.append("Favorable risk profile - good opportunity for investment")
        
        return recommendations