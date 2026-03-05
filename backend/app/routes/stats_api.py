from flask_restx import Resource, fields
from app.services.stats_service import StatsService


class OverviewStats(Resource):
    """Get general statistics about the database"""
    
    def get(self):
        """Get general statistics about the database"""
        try:
            stats = StatsService.get_overview_stats()
            return stats, 200
            
        except Exception as e:
            return {'error': f'Failed to fetch stats: {str(e)}'}, 500


class CountryStats(Resource):
    """Get pricing statistics grouped by country"""
    
    def get(self):
        """Get pricing statistics grouped by country"""
        try:
            stats = StatsService.get_stats_by_country()
            return stats, 200
            
        except Exception as e:
            return {'error': f'Failed to fetch country stats: {str(e)}'}, 500
