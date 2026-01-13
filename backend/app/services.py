import numpy as np
from typing import List, Dict, Any
from datetime import datetime, timedelta
from geopy.distance import geodesic
import logging

logger = logging.getLogger(__name__)

class IdeaPrioritizer:
    """Алгоритм интеллектуального ранжирования идей"""
    
    def __init__(self):
        self.weights = {
            'duplicate_factor': 0.4,
            'social_factor': 0.3,
            'infrastructure_factor': 0.3
        }
        
        self.thresholds = {
            'critical': 0.8,
            'high': 0.6,
            'medium': 0.4,
            'low': 0.2
        }
        
        self.analysis_radius = {
            'duplicate_search': 200,
            'infrastructure_search': 1000
        }
    
    def calculate_importance_score(self, idea: Dict, context: Dict) -> Dict:
        duplicate_score = self._calculate_duplicate_factor(
            idea['latitude'], 
            idea['longitude'], 
            idea['category'],
            context['similar_ideas']
        )
        
        social_score = self._calculate_social_factor(
            idea['votes_count'],
            idea['comments_count'],
            context['city_population']
        )
        
        infrastructure_score = self._calculate_infrastructure_factor(
            idea['latitude'],
            idea['longitude'],
            idea['category'],
            context['infrastructure_objects']
        )
        
        final_score = (
            duplicate_score * self.weights['duplicate_factor'] +
            social_score * self.weights['social_factor'] +
            infrastructure_score * self.weights['infrastructure_factor']
        )
        
        priority = self._determine_priority(final_score)
        
        explanation = self._generate_explanation(
            duplicate_score,
            social_score,
            infrastructure_score,
            priority
        )
        
        return {
            'final_score': round(final_score, 3),
            'priority': priority,
            'components': {
                'duplicate_score': round(duplicate_score, 3),
                'social_score': round(social_score, 3),
                'infrastructure_score': round(infrastructure_score, 3)
            },
            'weights': self.weights,
            'explanation': explanation,
            'recommended_action': self._get_recommended_action(priority)
        }
    
    def _calculate_duplicate_factor(self, lat: float, lon: float, 
                                   category: str, similar_ideas: List[Dict]) -> float:
        if not similar_ideas:
            return 0.3
        
        nearby_duplicates = 0
        total_similarity = 0
        
        for other_idea in similar_ideas:
            distance = geodesic((lat, lon), 
                               (other_idea['latitude'], other_idea['longitude'])).meters
            
            if distance <= self.analysis_radius['duplicate_search']:
                nearby_duplicates += 1
                
                days_diff = (datetime.now() - other_idea['created_at']).days
                time_factor = max(0, 1 - (days_diff / 30))
                
                total_similarity += time_factor
        
        max_expected = 10
        duplicate_factor = min(1.0, total_similarity / max_expected)
        
        if duplicate_factor > 0:
            duplicate_factor = np.log1p(duplicate_factor * 10) / np.log1p(10)
        
        return duplicate_factor
    
    def _calculate_social_factor(self, votes: int, comments: int, 
                                population: int) -> float:
        if population == 0:
            return 0.0
        
        engagement = votes + (comments * 2)
        normalized_engagement = engagement / (population / 10000)
        
        social_factor = 1 / (1 + np.exp(-(normalized_engagement - 5)))
        
        return min(1.0, social_factor)
    
    def _calculate_infrastructure_factor(self, lat: float, lon: float,
                                        category: str, 
                                        infrastructure: List[Dict]) -> float:
        category_to_infra = {
            'sport': ['football_field', 'playground', 'sport_complex'],
            'art': ['mural', 'sculpture', 'art_object'],
            'ecology': ['green_zone', 'park', 'waste_sorting'],
            'infrastructure': ['bench', 'lighting', 'road']
        }
        
        target_types = category_to_infra.get(category, [])
        
        if not target_types or not infrastructure:
            return 0.5
        
        min_distance = float('inf')
        closest_condition = 'unknown'
        
        for obj in infrastructure:
            if obj['type'] in target_types:
                distance = geodesic((lat, lon), 
                                   (obj['latitude'], obj['longitude'])).meters
                
                if distance < min_distance:
                    min_distance = distance
                    closest_condition = obj.get('condition', 'unknown')
        
        if min_distance == float('inf'):
            distance_factor = 1.0
        else:
            distance_factor = min(1.0, max(0.0, 
                1 - (min_distance / self.analysis_radius['infrastructure_search'])))
        
        condition_weights = {
            'poor': 0.8,
            'average': 0.5,
            'good': 0.2,
            'unknown': 0.5
        }
        
        condition_factor = condition_weights.get(closest_condition, 0.5)
        
        infrastructure_factor = (distance_factor * 0.7 + condition_factor * 0.3)
        
        return infrastructure_factor
    
    def _determine_priority(self, score: float) -> str:
        if score >= self.thresholds['critical']:
            return 'critical'
        elif score >= self.thresholds['high']:
            return 'high'
        elif score >= self.thresholds['medium']:
            return 'medium'
        else:
            return 'low'
    
    def _generate_explanation(self, dup_score: float, social_score: float,
                             infra_score: float, priority: str) -> Dict:
        explanations = []
        
        if dup_score > 0.7:
            explanations.append("Множество людей сообщают об этой же проблеме")
        elif dup_score > 0.4:
            explanations.append("Несколько людей отмечали похожие проблемы")
        
        if social_score > 0.7:
            explanations.append("Идея получила высокую поддержку сообщества")
        elif social_score > 0.4:
            explanations.append("Идея вызвала интерес у жителей")
        
        if infra_score > 0.7:
            explanations.append("В районе наблюдается острый дефицит подобных объектов")
        elif infra_score > 0.4:
            explanations.append("Существующая инфраструктура требует улучшений")
        
        if priority == 'critical':
            explanations.append("Требует немедленного рассмотрения")
        elif priority == 'high':
            explanations.append("Рекомендуется рассмотреть в первую очередь")
        
        return {
            'summary': f"Приоритет: {priority.upper()}",
            'details': explanations,
            'factors': [
                f"Повторяемость проблемы: {dup_score:.0%}",
                f"Поддержка жителей: {social_score:.0%}",
                f"Дефицит инфраструктуры: {infra_score:.0%}"
            ]
        }
    
    def _get_recommended_action(self, priority: str) -> Dict:
        actions = {
            'critical': {
                'timeframe': '24-48 часов',
                'action': 'Немедленно направить ответственной команде',
                'escalation': 'Уведомить руководство фонда'
            },
            'high': {
                'timeframe': '3-5 дней',
                'action': 'Включить в ближайший план работ',
                'escalation': 'Мониторинг статуса еженедельно'
            },
            'medium': {
                'timeframe': '1-2 недели',
                'action': 'Рассмотреть на плановом собрании',
                'escalation': 'Стандартная процедура'
            },
            'low': {
                'timeframe': '1 месяц',
                'action': 'Накопить статистику по похожим запросам',
                'escalation': 'Автоматический мониторинг'
            }
        }
        return actions.get(priority, actions['medium'])

class DataEnricher:
    """Обогащение данных"""
    
    @staticmethod
    def get_city_data(city_name: str) -> Dict:
        city_data = {
            'Киселёвск': {'population': 84369, 'area_sqkm': 160},
            'Барнаул': {'population': 632372, 'area_sqkm': 939},
            'Новокузнецк': {'population': 537480, 'area_sqkm': 424}
        }
        return city_data.get(city_name, {'population': 50000, 'area_sqkm': 100})
    
    @staticmethod
    def get_infrastructure_objects(lat: float, lon: float, radius: int = 1000) -> List[Dict]:
        # Заглушка - в реальности запрос к геосервису
        return [
            {'type': 'football_field', 'latitude': lat + 0.001, 
             'longitude': lon + 0.001, 'condition': 'good'},
            {'type': 'playground', 'latitude': lat + 0.002, 
             'longitude': lon + 0.002, 'condition': 'average'}
        ]

def update_idea_priority(db, idea_id):
    """Обновление приоритета идеи"""
    # Здесь будет вызов алгоритма ранжирования
    pass

def get_responsible_team(category: str, priority: str) -> str:
    """Определение ответственной команды"""
    teams = {
        'sport': 'Команда спортивных проектов',
        'art': 'Команда культурных проектов',
        'ecology': 'Команда экологических проектов',
        'infrastructure': 'Команда инфраструктуры'
    }
    return teams.get(category, 'Общая команда')

def send_notification(notification: dict):
    """Отправка уведомления"""
    # Заглушка - в реальности интеграция с email/telegram
    logger.info(f"Отправка уведомления: {notification}")