import requests
import json

class APIClient:
    def __init__(self, base_url="http://localhost:8000/api/v1"):
        self.base_url = base_url
    
    def get_suppliers(self, search_term=None, category=None, city=None):
        """קבלת רשימת ספקים"""
        url = f"{self.base_url}/suppliers"
        params = {}
        
        if search_term:
            params['search_term'] = search_term
        if category and category != "כל הקטגוריות":
            params['category'] = category
        if city and city != "כל הערים":
            params['city'] = city
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()['suppliers']
        except Exception as e:
            print(f"API Error: {e}")
            return []