from odoo import models, fields
import base64
import csv
import io
import logging

_logger = logging.getLogger(__name__)


class ImportPartListWizard(models.TransientModel):
    _name = 'import.partlist.wizard'
    _description = 'Import Part List Wizard'

    excel_file = fields.Binary(string='File CSV Part List', required=True)
    import_type = fields.Selection([
        ('single', 'Import một Model'),
        ('all', 'Import tất cả Model')
    ], string='Kiểu Import', default='single', required=True)

    def action_import_partlist(self):
        try:
            if self.import_type == 'single':
                # Import cho model hiện tại
                model_id = self.env.context.get('active_id')
                detail_model = self.env['detail.information'].browse(model_id)
                model_name = detail_model.name

                _logger.info(f"Import Part List cho model: {model_name}")
                model_counts = self.import_partlist_from_excel(self.excel_file, model_name)

            else:
                # Import cho tất cả model
                _logger.info("Import Part List cho tất cả model")
                model_counts = self.import_partlist_from_excel(self.excel_file)

            total_models = len(model_counts)
            total_records = sum(model_counts.values())

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thành công',
                    'message': f'Đã import {total_records} part list cho {total_models} model',
                    'type': 'success',
                }
            }

        except Exception as e:
            _logger.error(f"Lỗi khi import Part List: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lỗi',
                    'message': f'Có lỗi xảy ra: {str(e)}',
                    'type': 'danger',
                }
            }

    def import_partlist_from_excel(self, csv_data, model_name=None):
        """Import Part List từ file CSV"""
        try:
            _logger.info("Bắt đầu import part list")

            # Đọc file CSV
            csv_file = io.StringIO(base64.b64decode(csv_data).decode('utf-8'))
            reader = csv.reader(csv_file)

            # Bỏ qua hàng tiêu đề
            next(reader)

            model_counts = {}

            for row in reader:
                try:
                    excel_model = str(row[0]).strip()  # Cột Model (A)

                    if model_name and excel_model != model_name:
                        continue

                    detail_model = self.env['detail.information'].search([('name', '=', excel_model)], limit=1)
                    if not detail_model:
                        _logger.warning(f"Không tìm thấy model {excel_model} trong database")
                        continue

                    if excel_model not in model_counts:
                        detail_model.part_list_ids.unlink()
                        model_counts[excel_model] = 0

                    no = int(row[1])
                    component_code = str(row[2]).strip()
                    description = str(row[3]).strip()

                    component = self.env['component.information'].search([('name', '=', component_code)], limit=1)
                    if not component:
                        component = self.env['component.information'].create({
                            'name': component_code,
                            'description': description,
                            'model_ids': [(4, detail_model.id)]
                        })
                    else:
                        if detail_model.id not in component.model_ids.ids:
                            component.write({
                                'model_ids': [(4, detail_model.id)]
                            })

                    self.env['part.list.information'].create({
                        'model_name': detail_model.id,
                        'no': no,
                        'component_serial': component.id,
                        'description': description,
                        'quantity': 1
                    })

                    model_counts[excel_model] = model_counts.get(excel_model, 0) + 1

                except Exception as e:
                    _logger.error(f"Lỗi khi xử lý dòng: {str(e)}")
                    continue

            return model_counts

        except Exception as e:
            _logger.error(f"Lỗi khi đọc file CSV: {str(e)}")
            return {}