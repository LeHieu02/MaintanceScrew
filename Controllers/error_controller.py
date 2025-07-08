from odoo import http
from odoo.http import request
import json

class ErrorController(http.Controller):
    @http.route('/api/error/report', type='json', auth='public', methods=['POST'])
    def report_error(self, **kw):
        try:
            # Lấy dữ liệu từ request body và phân tích cú pháp JSON
            data = json.loads(request.httprequest.data)

            error_code = data.get('error_code')
            description = data.get('description')
            checked = data.get('checked')
            machine_code = data.get('machine_code')

            # Tìm máy theo mã máy (sử dụng sudo() để bỏ qua quyền truy cập)
            machine = request.env['machine.information'].sudo().search([('name','=',machine_code)], limit=1)
            if not machine:
                return {'status': 'error', 'message': f'Machine with code {machine_code} not found'}

            # Tạo bản ghi lỗi mới (sử dụng sudo() để bỏ qua quyền truy cập)
            error = request.env['error.information'].sudo().create({
                'error_code': error_code,
                'description': description,
                'checked': checked,
                'machine_id': machine.id
            })

            # Tìm leader và staff (sử dụng sudo() để đảm bảo tìm thấy)
            leader = request.env.ref('Maintenance_Screw.group_maintenance_leader').sudo().users[0]
            maintenance_staff = request.env.ref('Maintenance_Screw.group_maintenance_staff').sudo().users

            # Tạo thông báo cho leader (sử dụng sudo() để bỏ qua quyền truy cập)
            request.env['notification.history'].sudo().create({
                'name': request.env['ir.sequence'].sudo().next_by_code('notification.sequence') or '/',
                'notification_id': f'NT{request.env['ir.sequence'].sudo().next_by_code('notification.sequence')}',
                'sender_uid': request.env.user.id,
                'receiver_uid': leader.id,
                'title': f'Lỗi mới: {error_code}',
                'message': f'Phát hiện lỗi {error_code} trên máy {machine.name} ({machine.machine_serial}). Mô tả: {description}',
                'type_mess': 'to_leader',
                'status': 'unread'
            })

            # Tạo thông báo cho nhân viên bảo trì (sử dụng sudo() để bỏ qua quyền truy cập)
            for staff in maintenance_staff:
                request.env['notification.history'].sudo().create({
                    'name': request.env['ir.sequence'].sudo().next_by_code('notification.sequence') or '/',
                    'notification_id': f'NT{request.env['ir.sequence'].sudo().next_by_code('notification.sequence')}',
                    'sender_uid': request.env.user.id,
                    'receiver_uid': staff.id,
                    'title': f'Lỗi mới: {error_code}',
                    'message': f'Phát hiện lỗi {error_code} trên máy {machine.name} ({machine.machine_serial}). Mô tả: {description}',
                    'type_mess': 'to_staff',
                    'status': 'unread'
                })

            return {'status': 'success', 'message': 'Error reported successfully'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)} 