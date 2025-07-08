import logging
import os
from odoo import models, fields, api
import json
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

_logger = logging.getLogger(__name__)

def send_fcm_v1(token, title, body, project_id, credentials_json_path, data=None):
    _logger.info('=== START SENDING FCM NOTIFICATION ===')
    _logger.info('Token: %s', token)
    _logger.info('Title: %s', title)
    _logger.info('Body: %s', body)
    _logger.info('Project ID: %s', project_id)
    _logger.info('Credentials path: %s', credentials_json_path)
    
    try:
        # Kiểm tra file credentials có tồn tại không
        if not os.path.exists(credentials_json_path):
            _logger.error('Credentials file not found at path: %s', credentials_json_path)
            raise FileNotFoundError(f'Credentials file not found at path: {credentials_json_path}')
            
        credentials = service_account.Credentials.from_service_account_file(
            credentials_json_path,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"]
        )
        credentials.refresh(Request())
        access_token = credentials.token
        _logger.info('Access token obtained successfully')

        url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; UTF-8",
        }
        message = {
            "message": {
                "token": token,
                "notification": {
                    "title": title,
                    "body": body
                },
                "data": data or {}
            }
        }
        _logger.info('Sending request to FCM...')
        response = requests.post(url, headers=headers, data=json.dumps(message))
        _logger.info('FCM Response: %s', response.json())
        return response.json()
    except Exception as e:
        _logger.error('Error sending FCM notification: %s', str(e))
        raise e

class NotificationHistory(models.Model):
    _name = 'notification.history'
    _description = 'Notification History'

    name = fields.Char(string='ID', required=True)
    notification_id = fields.Char(string='NotificationID', required=True)
    sender_uid = fields.Integer(string='Sender UID', required=True)
    receiver_uid = fields.Integer(string='Receiver UID', required=True)
    title = fields.Char(string='Title', required=True)
    message = fields.Char(string='Message')
    type = fields.Char(string='Type')
    maintenance_id = fields.Many2one('maintenance.information', string='Maintenance Reference')
    type_mess = fields.Selection([
        ('to_leader', 'Notification to Leader'),
        ('to_staff', 'Notification to Staff'),
        ('to_warehousestaff', 'Notification to Warehouse Staff')
    ], string='Type', required=True)
    send_date = fields.Datetime(string='SendDate', default=fields.Datetime.now)
    status = fields.Selection([
        ('unread', 'Unread'),
        ('read', 'Read')
    ], string='Status', default='unread')

    @api.model
    def notify_maintenance_status(self, maintenance_record, type_mess):
        _logger.info('=== START NOTIFICATION ===')
        _logger.info('Maintenance: %s, Type: %s, User: %s',
                      maintenance_record.name,
                      type_mess,
                      self.env.user.id)
        
        try:
            if type_mess == 'to_leader':
                message = f"One record of maintenance [{maintenance_record.name}] has been status Waiting and need to be confirmed !"
                receiver = self.env.ref('Maintenance_Screw.group_maintenance_leader').users[0]
                title = 'Maintenance Leader Confirmation'
                _logger.info('Leader Receiver ID: %s', receiver.id)
            else:  # to_staff
                if maintenance_record.status == 'processing':
                    message = f"One record of maintenance [{maintenance_record.name}] has been denied and returned to Processing status!"
                else:
                    message = f"One record of maintenance [{maintenance_record.name}] has confirmed and changed to status: {maintenance_record.status}!"
                receiver = maintenance_record.create_uid
                title = 'Maintenance Staff Notification'
                _logger.info('Staff Receiver ID: %s', receiver.id)

            # Create notification history
            notification = self.create({
                'name': self.env['ir.sequence'].next_by_code('notification.sequence') or '/',
                'notification_id': f'NT{fields.Datetime.now().strftime("%Y%m%d%H%M%S")}',
                'sender_uid': self.env.user.id,
                'receiver_uid': receiver.id,
                'title': title,
                'message': message,
                'maintenance_id': maintenance_record.id,
                'type_mess': type_mess,
                'status': 'unread'
            })
            _logger.info('Notification history created successfully')

            # Gửi FCM notification
            fcm_token_obj = self.env['fcm.token'].search([('uid', '=', str(receiver.id))], limit=1)
            _logger.info('FCM Token found: %s', bool(fcm_token_obj))
            
            if fcm_token_obj and fcm_token_obj.token:
                # Sử dụng đường dẫn tương đối
                addon_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                credentials_path = os.path.join(addon_path, 'firebase_config', 'firebase-credentials.json')
                project_id = 'maintenancescrew-b8db2'
                
                _logger.info('Using credentials path: %s', credentials_path)
                
                try:
                    send_fcm_v1(
                        token=fcm_token_obj.token,
                        title=notification.title,
                        body=notification.message,
                        project_id=project_id,
                        credentials_json_path=credentials_path
                    )
                    _logger.info('FCM notification sent successfully')
                except Exception as e:
                    _logger.error('Error sending FCM notification: %s', str(e))
                    self.env['ir.logging'].create({
                        'name': 'FCM Error',
                        'type': 'server',
                        'level': 'error',
                        'message': str(e),
                        'path': __file__,
                        'line': '0',
                        'func': 'notify_maintenance_status',
                    })
            else:
                _logger.warning('No FCM token found for user %s', receiver.id)

            # Send instant notification
            self.env['bus.bus']._sendone(
                receiver.partner_id,
                'ir.notification',
                {
                    'type': 'info',
                    'title': notification.title,
                    'message': notification.message,
                    'sticky': True,
                }
            )
            _logger.info('Instant notification sent successfully')
            return notification
            
        except Exception as e:
            _logger.error('Error in notify_maintenance_status: %s', str(e))
            raise e

    def notify_export_status(self, export_record, notify_type, message=None):
        if notify_type == 'to_leader':
            message = message or f"Export record [{export_record.export_code}] for maintenance [{export_record.maintenance_id.name}] needs confirmation!"
            receiver = self.env.ref('Maintenance_Screw.group_maintenance_leader').users[0]
            title = 'Export Leader Confirmation'
        elif notify_type == 'to_warehousestaff':
            message = message or f"Export record [{export_record.export_code}] has been confirmed and needs processing!"
            receiver = self.env.ref('Maintenance_Screw.group_warehouse_staff').users[0]
            title = 'Warehouse Staff Processing'
        else:  # to_staff
            message = message or f"Export record [{export_record.export_code}] has been confirmed by leader!"
            receiver = export_record.create_uid
            title = 'Export Staff Notification'

        notification = self.create({
            'name': self.env['ir.sequence'].next_by_code('notification.sequence') or '/',
            'notification_id': f'NT{fields.Datetime.now().strftime("%Y%m%d%H%M%S")}',
            'sender_uid': self.env.user.id,
            'receiver_uid': receiver.id,
            'title': title,
            'message': message,
            'maintenance_id': export_record.maintenance_id.id,
            'type_mess': notify_type,
            'status': 'unread'
        })

    def action_open_record(self):
        self.write({'status': 'read'})
        if 'maintenance' in self.message.lower() and 'export' not in self.message.lower():
            # Mở maintenance record
            maintenance = self.maintenance_id
            if maintenance:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'maintenance.information',
                    'res_id': maintenance.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
        elif 'export' in self.message.lower():
            # Tìm mã export trong message
            try:
                export_code = self.message.split('[')[1].split(']')[0]
                export = self.env['export.information'].search([('export_code', '=', export_code)], limit=1)
                if export:
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'export.information',
                        'res_id': export.id,
                        'view_mode': 'form',
                        'target': 'current',
                    }
            except:
                # Nếu không tìm thấy mã export trong dấu [], thử tìm theo cách khác
                words = self.message.split()
                for i, word in enumerate(words):
                    if word.upper().startswith('EXP'):
                        export_code = word
                        export = self.env['export.information'].search([('export_code', '=', export_code)], limit=1)
                        if export:
                            return {
                                'type': 'ir.actions.act_window',
                                'res_model': 'export.information',
                                'res_id': export.id,
                                'view_mode': 'form',
                                'target': 'current',
                            }
    @api.model
    def get_notifications_for_user(self, user_id):
        current_user = self.env.user.id
        notifications = self.search([('receiver_uid', '=', current_user)], order='send_date desc', limit=50)
        result = []
        for n in notifications:
            result.append({
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'maintenanceId': n.maintenance_id.id if n.maintenance_id else "",
                'typeMess': n.type_mess,
                'timestamp': n.send_date and n.send_date.strftime('%Y-%m-%d %H:%M:%S') or "",
                'status': n.status,
            })
        return result

    @api.model
    def mark_as_read(self, notification_id):
        notification = self.browse(notification_id)
        if notification:
            notification.status = 'read'
            return True
        return False

    @api.model
    def delete_notification(self, notification_id):
        notification = self.browse(notification_id)
        if notification:
            notification.unlink()
            return True
        return False

class FcmToken(models.Model):
    _name = 'fcm.token'
    _description = 'FCM Token Information'

    name = fields.Char(string='ID', required=True)
    token = fields.Char(string='Token', required=True)
    uid = fields.Char(string='UID', required=True)