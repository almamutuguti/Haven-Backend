import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import EmergencyHospitalCommunication

class HospitalCommunicationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.communication_id = self.scope['url_route']['kwargs']['communication_id']
        self.room_group_name = f'communication_{self.communication_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current status
        current_status = await self.get_communication_status()
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'status': current_status
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'message': 'alive'
            }))
    
    # Receive message from room group
    async def communication_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'status': event['status'],
            'message': event.get('message', ''),
            'timestamp': event.get('timestamp', '')
        }))
    
    @database_sync_to_async
    def get_communication_status(self):
        try:
            communication = EmergencyHospitalCommunication.objects.get(id=self.communication_id)
            return {
                'status': communication.status,
                'hospital_ready': all([
                    communication.doctors_ready,
                    communication.nurses_ready,
                    communication.equipment_ready,
                    communication.bed_ready
                ]),
                'estimated_arrival_minutes': communication.estimated_arrival_minutes,
                'patient_arrived': communication.patient_arrived_at is not None
            }
        except EmergencyHospitalCommunication.DoesNotExist:
            return {'status': 'unknown'}