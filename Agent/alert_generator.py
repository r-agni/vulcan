"""
Alert Generator - Gemini-powered intelligent alert system
Analyzes real-time data and generates contextual alerts
"""

from google import genai
from google.genai import types
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from .alert_types import Alert, AlertPriority, AlertCategory, AlertRecipient
from .alert_rules import AlertRules


class AlertGenerator:
    """Generate intelligent alerts using Gemini AI"""
    
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        self.rules = AlertRules()
        
    def analyze_and_generate_alerts(
        self,
        analytics_data: Dict[str, Any],
        behavior_analysis: Optional[str] = None,
        timestamp_data: Optional[Dict[str, Any]] = None
    ) -> List[Alert]:
        """
        Main method to analyze data and generate alerts
        
        Args:
            analytics_data: Current analytics (occupancy, dwell times, queue data, etc.)
            behavior_analysis: Gemini-generated behavior analysis text
            timestamp_data: Per-timestamp analytical data
        
        Returns:
            List of Alert objects
        """
        alerts = []
        
        # Rule-based alerts (fast, deterministic)
        rule_alerts = self._generate_rule_based_alerts(analytics_data)
        alerts.extend(rule_alerts)
        
        # Behavior-based alerts (from existing analysis)
        if behavior_analysis:
            behavior_alerts = self._generate_behavior_alerts(
                behavior_analysis,
                analytics_data
            )
            alerts.extend(behavior_alerts)
        
        # AI-generated contextual alerts (intelligent, context-aware)
        if analytics_data or timestamp_data:
            ai_alerts = self._generate_ai_alerts(
                analytics_data,
                behavior_analysis,
                timestamp_data
            )
            alerts.extend(ai_alerts)
        
        return alerts
    
    def _generate_rule_based_alerts(self, analytics_data: Dict[str, Any]) -> List[Alert]:
        """Generate alerts based on predefined rules"""
        alerts = []
        
        # Check dwell times
        if 'dwell_times' in analytics_data:
            for zone_data in analytics_data['dwell_times']:
                person_id = zone_data.get('person_id')
                zone_id = zone_data.get('zone_id')
                zone_name = zone_data.get('zone_name', f'Zone {zone_id}')
                dwell_time = zone_data.get('duration', 0)
                zone_type = zone_data.get('zone_type', 'product')
                
                rule_result = self.rules.should_alert_long_dwell(dwell_time, zone_type)
                if rule_result:
                    alert = Alert(
                        id=f"dwell_{person_id}_{zone_id}_{int(datetime.now().timestamp())}",
                        title=f"Customer in {zone_name}",
                        message=rule_result['reason'],
                        priority=rule_result['priority'],
                        category=rule_result['category'],
                        recipient=rule_result['recipient'],
                        timestamp=datetime.now(),
                        person_id=person_id,
                        zone_id=zone_id,
                        zone_name=zone_name,
                        context_data={'dwell_time': dwell_time}
                    )
                    alerts.append(alert)
        
        # Check queue metrics
        if 'queue_metrics' in analytics_data:
            for queue_data in analytics_data['queue_metrics']:
                zone_id = queue_data.get('zone_id')
                zone_name = queue_data.get('zone_name', 'Checkout')
                queue_length = queue_data.get('queue_length', 0)
                avg_wait = queue_data.get('avg_wait_time')
                
                rule_result = self.rules.should_alert_queue(queue_length, avg_wait)
                if rule_result:
                    alert = Alert(
                        id=f"queue_{zone_id}_{int(datetime.now().timestamp())}",
                        title=f"Queue Alert: {zone_name}",
                        message=rule_result['reason'],
                        priority=rule_result['priority'],
                        category=rule_result['category'],
                        recipient=rule_result['recipient'],
                        timestamp=datetime.now(),
                        zone_id=zone_id,
                        zone_name=zone_name,
                        context_data={'queue_length': queue_length, 'avg_wait_time': avg_wait}
                    )
                    alerts.append(alert)
        
        # Check occupancy
        if 'occupancy' in analytics_data:
            for occ_data in analytics_data['occupancy']:
                zone_id = occ_data.get('zone_id')
                zone_name = occ_data.get('zone_name', 'Store')
                current = occ_data.get('current', 0)
                capacity = occ_data.get('capacity', 0)
                
                if capacity > 0:
                    rule_result = self.rules.should_alert_occupancy(current, capacity)
                    if rule_result:
                        alert = Alert(
                            id=f"occupancy_{zone_id}_{int(datetime.now().timestamp())}",
                            title=f"Capacity Alert: {zone_name}",
                            message=rule_result['reason'],
                            priority=rule_result['priority'],
                            category=rule_result['category'],
                            recipient=rule_result['recipient'],
                            timestamp=datetime.now(),
                            zone_id=zone_id,
                            zone_name=zone_name,
                            context_data={'current': current, 'capacity': capacity}
                        )
                        alerts.append(alert)
        
        return alerts
    
    def _generate_behavior_alerts(
        self,
        behavior_analysis: str,
        analytics_data: Dict[str, Any]
    ) -> List[Alert]:
        """Generate alerts from behavior analysis text"""
        alerts = []
        
        # Analyze behavior text using rules
        rule_results = self.rules.analyze_behavior_text(behavior_analysis)
        
        for result in rule_results:
            person_id = analytics_data.get('person_id')
            zone_id = analytics_data.get('zone_id')
            zone_name = analytics_data.get('zone_name', 'Store')
            
            alert = Alert(
                id=f"behavior_{person_id}_{int(datetime.now().timestamp())}",
                title=result['reason'],
                message=result.get('context', behavior_analysis[:200]),
                priority=result['priority'],
                category=result['category'],
                recipient=result['recipient'],
                timestamp=datetime.now(),
                person_id=person_id,
                zone_id=zone_id,
                zone_name=zone_name,
                context_data={'behavior_snippet': behavior_analysis[:500]}
            )
            alerts.append(alert)
        
        return alerts
    
    def _generate_ai_alerts(
        self,
        analytics_data: Dict[str, Any],
        behavior_analysis: Optional[str],
        timestamp_data: Optional[Dict[str, Any]]
    ) -> List[Alert]:
        """Generate intelligent alerts using Gemini AI"""
        try:
            # Prepare context for Gemini
            context = self._prepare_context(analytics_data, behavior_analysis, timestamp_data)

            # Extract actual person IDs from the data to prevent hallucination
            actual_person_ids = set()
            if 'dwell_times' in analytics_data:
                actual_person_ids.update(d.get('person_id') for d in analytics_data['dwell_times'] if d.get('person_id'))
            if timestamp_data and 'active_persons' in timestamp_data:
                actual_person_ids.update(timestamp_data['active_persons'])

            # Create explicit list of valid person IDs
            person_id_list = list(actual_person_ids) if actual_person_ids else []
            person_constraint = f"\nVALID PERSON IDs ONLY: {person_id_list}" if person_id_list else "\nNo person IDs available - Generate only operational/manager alerts if needed."

            prompt = f"""
            You are an intelligent retail surveillance alert system. Analyze the following real-time data and generate actionable alerts for store staff.

            CURRENT SITUATION:
            {context}
            {person_constraint}

            TASK: Generate alerts in JSON format following this structure:
            {{
              "alerts": [
                {{
                  "title": "Brief alert title (e.g., 'Customer in Electronics')",
                  "message": "Concise, actionable message for quick reading",
                  "priority": "low|medium|high|critical",
                  "category": "customer_service|queue_management|security|operations|capacity",
                  "recipient": "salesperson|manager|both",
                  "person_id": null or number from VALID PERSON IDs list ONLY,
                  "zone_id": null or number,
                  "zone_name": "zone name if applicable",
                  "person_details": {{
                    "behavior_summary": "Key behaviors observed from the data",
                    "zone_history": "Which zones visited and for how long (from data provided)",
                    "engagement_level": "low|medium|high",
                    "purchase_intent": "Brief assessment based on dwell time and zone visits",
                    "recommended_approach": "Specific suggestion for salesperson"
                  }}
                }}
              ]
            }}

            CRITICAL RULES TO PREVENT HALLUCINATION:
            1. ONLY use person_id values from the VALID PERSON IDs list above
            2. DO NOT invent person IDs, demographics, or appearance details
            3. DO NOT create alerts for people not in the provided data
            4. Base all alerts STRICTLY on the provided analytics data
            5. If no person data is available, generate only operational/manager alerts

            ALERT PRIORITY GUIDELINES:

            For SALESPERSON alerts (when valid person data exists):
            - Customer showing interest (2+ minutes in any product zone - check DWELL TIMES data)
            - Customer in multiple zones (check zone_history from data)
            - High dwell time customers needing assistance
            - MUST use valid person_id from list above
            - person_details should reflect ACTUAL data provided, not assumptions

            For MANAGER alerts:
            - Critical operational issues (long queues, capacity warnings from provided data)
            - Staffing needs based on occupancy data
            - Customer satisfaction risks based on queue metrics
            - General store operations

            PERSON DETAILS REQUIREMENTS:
            - Only include person_details if you have a valid person_id from the list
            - Base behavior_summary ONLY on provided dwell time and zone data
            - Do NOT invent demographics, appearance, or other details
            - Focus on actionable behavioral insights from the actual data

            IMPORTANT:
            - Generate 2-5 alerts based on ACTUAL data available
            - Quality over quantity - only alert on real observations
            - If person data is limited, focus more on operational alerts
            - NEVER use person IDs not in the VALID PERSON IDs list

            Provide ONLY the JSON response, no additional text.
            """
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt]
            )
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Extract JSON from markdown code blocks if present
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            elif response_text.startswith('```') and response_text.endswith('```'):
                response_text = response_text.strip('`').strip()
                if response_text.startswith('json'):
                    response_text = response_text[4:].strip()
            
            alert_data = json.loads(response_text)
            
            # Convert to Alert objects with validation
            alerts = []
            for alert_dict in alert_data.get('alerts', [])[:8]:  # Limit to 8 alerts
                try:
                    person_id = alert_dict.get('person_id')

                    # VALIDATION: If alert has a person_id, it MUST be in our valid list
                    if person_id is not None:
                        if person_id not in person_id_list:
                            print(f"REJECTED HALLUCINATED ALERT: person_id {person_id} not in valid list {person_id_list}")
                            continue  # Skip this hallucinated alert

                    # Additional validation: salesperson alerts MUST have person_id
                    if alert_dict['recipient'] == 'salesperson' and person_id is None:
                        print(f"REJECTED: Salesperson alert without person_id: {alert_dict['title']}")
                        continue

                    alert = Alert(
                        id=f"ai_{int(datetime.now().timestamp())}_{len(alerts)}",
                        title=alert_dict['title'],
                        message=alert_dict['message'],
                        priority=AlertPriority(alert_dict['priority']),
                        category=AlertCategory(alert_dict['category']),
                        recipient=AlertRecipient(alert_dict['recipient']),
                        timestamp=datetime.now(),
                        person_id=person_id,
                        zone_id=alert_dict.get('zone_id'),
                        zone_name=alert_dict.get('zone_name'),
                        context_data={'source': 'ai_generated'},
                        person_details=alert_dict.get('person_details')
                    )
                    alerts.append(alert)
                except (KeyError, ValueError) as e:
                    print(f"Error parsing alert: {e}")
                    continue

            return alerts
            
        except json.JSONDecodeError as e:
            print(f"Error parsing Gemini JSON response: {e}")
            print(f"Raw response: {response.text}")
            return []
        except Exception as e:
            print(f"Error generating AI alerts: {e}")
            return []
    
    def _prepare_context(
        self,
        analytics_data: Dict[str, Any],
        behavior_analysis: Optional[str],
        timestamp_data: Optional[Dict[str, Any]]
    ) -> str:
        """Prepare context string for Gemini"""
        context_parts = []
        
        # Current analytics summary
        if analytics_data:
            context_parts.append("CURRENT ANALYTICS:")
            
            if 'occupancy' in analytics_data:
                context_parts.append(f"- Total customers in store: {analytics_data.get('total_occupancy', 0)}")
                for zone in analytics_data['occupancy']:
                    context_parts.append(
                        f"  - {zone.get('zone_name')}: {zone.get('current', 0)}/{zone.get('capacity', 'unlimited')} customers"
                    )
            
            if 'dwell_times' in analytics_data:
                context_parts.append("\nCUSTOMER DWELL TIMES:")
                for dwell in analytics_data['dwell_times']:
                    duration_min = int(dwell.get('duration', 0) / 60)
                    context_parts.append(
                        f"  - Person {dwell.get('person_id')} in {dwell.get('zone_name')}: {duration_min} minutes"
                    )
            
            if 'queue_metrics' in analytics_data:
                context_parts.append("\nQUEUE STATUS:")
                for queue in analytics_data['queue_metrics']:
                    context_parts.append(
                        f"  - {queue.get('zone_name')}: {queue.get('queue_length', 0)} customers waiting"
                    )
                    if queue.get('avg_wait_time'):
                        avg_wait_min = int(queue.get('avg_wait_time', 0) / 60)
                        context_parts.append(f"    Average wait: {avg_wait_min} minutes")
        
        # Behavior analysis
        if behavior_analysis:
            context_parts.append(f"\nRECENT BEHAVIOR ANALYSIS:\n{behavior_analysis[:1000]}")
        
        # Timestamp-specific data
        if timestamp_data:
            context_parts.append(f"\nTIMESTAMP DATA:\n{json.dumps(timestamp_data, indent=2)[:500]}")
        
        return "\n".join(context_parts)
    
    def generate_summary_alert(self, period: str = "hourly") -> Optional[Alert]:
        """Generate periodic summary alert for managers"""
        try:
            prompt = f"""
            Generate a brief {period} summary alert for store management.
            
            Provide a concise overview of:
            - Overall store performance
            - Any notable patterns or concerns
            - Actionable recommendations
            
            Keep it under 100 words. Focus on what managers need to know.
            """
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt]
            )
            
            return Alert(
                id=f"summary_{period}_{int(datetime.now().timestamp())}",
                title=f"{period.capitalize()} Summary",
                message=response.text,
                priority=AlertPriority.LOW,
                category=AlertCategory.OPERATIONS,
                recipient=AlertRecipient.MANAGER,
                timestamp=datetime.now(),
                context_data={'type': 'summary', 'period': period}
            )
            
        except Exception as e:
            print(f"Error generating summary alert: {e}")
            return None
