import numpy as np
from typing import List, Dict, Tuple
import re
from collections import Counter
import logging

logger = logging.getLogger(__name__)

class SimpleAICategorizer:
    """
    Упрощенный AI для категоризации идей
    В реальности здесь будет нейросеть или ML модель
    """
    
    def __init__(self):
        # Ключевые слова для категорий
        self.category_keywords = {
            'sport': [
                'футбол', 'спорт', 'площадка', 'стадион', 'тренажер',
                'бег', 'зал', 'бассейн', 'турник', 'мяч'
            ],
            'art': [
                'мурал', 'картина', 'искусство', 'красивый', 'стена',
                'рисунок', 'художник', 'граффити', 'скульптура'
            ],
            'ecology': [
                'дерево', 'зеленый', 'мусор', 'экология', 'чистый',
                'озеленение', 'цветы', 'свалка', 'отходы', 'воздух'
            ],
            'infrastructure': [
                'дорога', 'тротуар', 'освещение', 'ремонт', 'лавочка',
                'парковка', 'остановка', 'мост', 'фонтан'
            ],
            'culture': [
                'библиотека', 'музей', 'театр', 'концерт', 'фестиваль',
                'выставка', 'праздник', 'традиция'
            ],
            'education': [
                'школа', 'детский', 'образование', 'кружок', 'лаборатория',
                'учебный', 'студент', 'учитель'
            ]
        }
        
        # Синонимы и стоп-слова
        self.synonyms = {
            'футбольный': 'футбол',
            'спортивный': 'спорт',
            'экологический': 'экология'
        }
        
    def categorize(self, text: str, title: str = "") -> Dict:
        """
        Определяет категорию идеи на основе текста
        Возвращает вероятности для всех категорий
        """
        
        full_text = (title + " " + text).lower()
        
        # Предобработка текста
        tokens = self._preprocess_text(full_text)
        
        # Подсчет совпадений с ключевыми словами
        scores = {}
        total_matches = 0
        
        for category, keywords in self.category_keywords.items():
            matches = 0
            for token in tokens:
                if token in keywords:
                    matches += 1
                # Проверка синонимов
                elif token in self.synonyms and self.synonyms[token] in keywords:
                    matches += 0.8  # Синонимы весят меньше
            
            scores[category] = matches
            total_matches += matches
        
        # Нормализация и добавление базовой вероятности
        if total_matches > 0:
            for category in scores:
                scores[category] = scores[category] / total_matches
        else:
            # Если нет совпадений - равномерное распределение
            for category in self.category_keywords:
                scores[category] = 1 / len(self.category_keywords)
        
        # Определение основной категории
        main_category = max(scores.items(), key=lambda x: x[1])
        
        return {
            'main_category': main_category[0],
            'confidence': main_category[1],
            'all_scores': scores,
            'tokens_analyzed': len(tokens)
        }
    
    def find_duplicates(self, text: str, existing_ideas: List[Dict]) -> List[Dict]:
        """
        Поиск потенциальных дубликатов идеи
        Использует семантическое сходство (упрощенное)
        """
        
        duplicates = []
        text_tokens = set(self._preprocess_text(text))
        
        for idea in existing_ideas:
            idea_tokens = set(self._preprocess_text(idea['description']))
            
            # Вычисление коэффициента Жаккара
            intersection = len(text_tokens.intersection(idea_tokens))
            union = len(text_tokens.union(idea_tokens))
            
            if union > 0:
                similarity = intersection / union
                
                if similarity > 0.3:  # Порог сходства
                    duplicates.append({
                        'idea_id': idea['id'],
                        'similarity': similarity,
                        'title': idea['title'],
                        'reason': self._explain_similarity(text_tokens, idea_tokens)
                    })
        
        return sorted(duplicates, key=lambda x: x['similarity'], reverse=True)
    
    def _preprocess_text(self, text: str) -> List[str]:
        """Очистка и токенизация текста"""
        # Удаление спецсимволов, приведение к нижнему регистру
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Разделение на слова
        tokens = text.split()
        
        # Удаление стоп-слов (можно расширить)
        stop_words = {'и', 'в', 'на', 'не', 'что', 'это', 'для', 'по', 'к', 'у'}
        tokens = [t for t in tokens if t not in stop_words and len(t) > 2]
        
        return tokens
    
    def _explain_similarity(self, tokens1: set, tokens2: set) -> str:
        """Генерация объяснения сходства"""
        common = tokens1.intersection(tokens2)
        if len(common) > 3:
            return f"Общие ключевые слова: {', '.join(list(common)[:3])}"
        return "Контекстуальное сходство"
