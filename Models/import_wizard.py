from odoo import models, fields
import base64
import os
import logging
import zipfile
import tempfile
import shutil

_logger = logging.getLogger(__name__)


class ImportPartScanWizard(models.TransientModel):
    _name = 'import.partscan.wizard'
    _description = 'Import Part Scan Wizard'

    folder_path = fields.Char(string='Đường dẫn thư mục gốc', required=True)
    import_type = fields.Selection([
        ('single', 'Import một Model'),
        ('all', 'Import tất cả Model')
    ], string='Kiểu Import', default='single', required=True)

    def extract_zip(self, zip_path, extract_path):
        """Giải nén file ZIP"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            return True
        except Exception as e:
            _logger.error(f"Lỗi khi giải nén file {zip_path}: {str(e)}")
            return False

    def import_model_images(self, model_folder_path, detail_model):
        """Import ảnh cho một model cụ thể"""
        counter = 1
        temp_dir = None
        _logger.info(f"Bắt đầu import ảnh từ thư mục: {model_folder_path}")

        def process_directory(dir_path):
            nonlocal counter
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)

                # Nếu là file ZIP
                if item.lower().endswith('.zip'):
                    _logger.info(f"Tìm thấy file ZIP: {item_path}")
                    # Tạo thư mục tạm để giải nén
                    temp_extract_path = tempfile.mkdtemp()
                    if self.extract_zip(item_path, temp_extract_path):
                        # Xử lý các file trong thư mục giải nén
                        process_directory(temp_extract_path)
                    # Xóa thư mục tạm sau khi xử lý xong
                    shutil.rmtree(temp_extract_path)

                # Nếu là thư mục
                elif os.path.isdir(item_path):
                    _logger.info(f"Tìm thấy thư mục con: {item_path}")
                    process_directory(item_path)

                # Nếu là file ảnh
                elif item.lower().endswith(('.png', '.jpg', '.jpeg', '.svg')):
                    _logger.info(f"Import ảnh: {item_path}")
                    try:
                        with open(item_path, 'rb') as img_file:
                            image_data = base64.b64encode(img_file.read())

                        self.env['part.scan.information'].create({
                            'model_name': detail_model.id,
                            'no': counter,
                            'image': image_data,
                        })
                        _logger.info(f"Đã import thành công ảnh số {counter}")
                        counter += 1
                    except Exception as e:
                        _logger.error(f"Lỗi khi import ảnh {item_path}: {str(e)}")

        if os.path.exists(model_folder_path):
            process_directory(model_folder_path)
        else:
            _logger.warning(f"Thư mục không tồn tại: {model_folder_path}")

        return counter - 1

    def action_import_partscan(self, _logger=None):
        try:
            base_path = self.folder_path.strip()
            _logger.info(f"Đường dẫn gốc: {base_path}")
            total_models = 0
            total_images = 0

            if self.import_type == 'single':
                model_id = self.env.context.get('active_id')
                detail_model = self.env['detail.information'].browse(model_id)
                model_name = detail_model.name

                _logger.info(f"Model ID: {model_id}")
                _logger.info(f"Tên model cần import: {model_name}")

                # Xóa part scan cũ
                detail_model.part_scan_ids.unlink()

                # Tìm thư mục model
                for root, dirs, files in os.walk(base_path):
                    if os.path.basename(root) == model_name:
                        _logger.info(f"Tìm thấy thư mục model tại: {root}")
                        images_count = self.import_model_images(root, detail_model)
                        total_images += images_count
                        if images_count > 0:
                            total_models = 1

            else:
                # Import cho tất cả model
                detail_models = self.env['detail.information'].search([])
                for detail_model in detail_models:
                    model_name = detail_model.name
                    if not model_name:
                        continue

                    # Xóa part scan cũ của model này
                    detail_model.part_scan_ids.unlink()

                    # Tìm thư mục model
                    for root, dirs, files in os.walk(base_path):
                        if os.path.basename(root) == model_name:
                            images_count = self.import_model_images(root, detail_model)
                            if images_count > 0:
                                total_models += 1
                                total_images += images_count

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Thành công',
                    'message': f'Đã import {total_images} ảnh cho {total_models} model',
                    'type': 'success',
                }
            }

        except Exception as e:
            _logger.error("Lỗi khi import Part Scan: %s", str(e))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lỗi',
                    'message': f'Có lỗi xảy ra: {str(e)}',
                    'type': 'danger',
                }
            }

        from odoo import models, fields
        import base64
        import xlrd
        import logging

        _logger = logging.getLogger(__name__)

        class ImportPartListWizard(models.TransientModel):
            _name = 'import.partlist.wizard'
            _description = 'Import Part List Wizard'

            excel_file = fields.Binary(string='File Excel Part List', required=True)
            import_type = fields.Selection([
                ('single', 'Import một Model'),
                ('all', 'Import tất cả Model')
            ], string='Kiểu Import', default='single', required=True)

            def import_partlist_from_excel(self, excel_data, model_name=None):
                """Import Part List từ file Excel"""
                try:
                    # Đọc file Excel
                    workbook = xlrd.open_workbook(file_contents=base64.b64decode(excel_data))
                    sheet = workbook.sheet_by_index(0)

                    # Dictionary để theo dõi số lượng record đã import cho mỗi model
                    model_counts = {}

                    # Bỏ qua hàng tiêu đề
                    for row in range(1, sheet.nrows):
                        excel_model = sheet.cell(row, 0).value  # Cột Model (A)

                        # Nếu import một model cụ thể, bỏ qua các model khác
                        if model_name and excel_model != model_name:
                            continue

                        # Tìm model trong database
                        detail_model = self.env['detail.information'].search([('name', '=', excel_model)], limit=1)
                        if not detail_model:
                            _logger.warning(f"Không tìm thấy model {excel_model} trong database")
                            continue

                        # Xóa part list cũ nếu là record đầu tiên của model này
                        if excel_model not in model_counts:
                            detail_model.part_list_ids.unlink()
                            model_counts[excel_model] = 0

                        try:
                            # Tạo part list mới
                            self.env['part.list.information'].create({
                                'model_name': detail_model.id,
                                'no': int(sheet.cell(row, 1).value),  # Cột No (B)
                                'component_serial': sheet.cell(row, 2).value,  # Cột Component (C)
                                'description': sheet.cell(row, 3).value,  # Cột Description (D)
                                'quantity': 1  # Mặc định số lượng là 1
                            })
                            model_counts[excel_model] += 1

                        except Exception as e:
                            _logger.error(f"Lỗi khi import dòng {row + 1}: {str(e)}")

                    return model_counts

                except Exception as e:
                    _logger.error(f"Lỗi khi đọc file Excel: {str(e)}")
                    return {}

            def action_import_partlist(self):
                try:
                    if self.import_type == 'single':
                        # Import cho model hiện tại
                        model_id = self.env.context.get('active_id')
                        detail_model = self.env['detail.information'].browse(model_id)
                        model_name = detail_model.name

                        _logger.info(f"Import Part List cho model: {model_name}")
                        model_counts = self.import_partlist_from_excel(self.excel_file, model_name)

                        total_models = len(model_counts)
                        total_records = sum(model_counts.values())

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


from odoo import models, fields
import base64
import xlrd
import logging

_logger = logging.getLogger(__name__)


class ImportPartListWizard(models.TransientModel):
    _name = 'import.partlist.wizard'
    _description = 'Import Part List Wizard'

    excel_file = fields.Binary(string='File Excel Part List', required=True)
    import_type = fields.Selection([
        ('single', 'Import một Model'),
        ('all', 'Import tất cả Model')
    ], string='Kiểu Import', default='single', required=True)

    def import_partlist_from_excel(self, excel_data, model_name=None):
        """Import Part List từ file Excel"""
        try:
            # Đọc file Excel
            workbook = xlrd.open_workbook(file_contents=base64.b64decode(excel_data))
            sheet = workbook.sheet_by_index(0)

            # Dictionary để theo dõi số lượng record đã import cho mỗi model
            model_counts = {}

            # Bỏ qua hàng tiêu đề
            for row in range(1, sheet.nrows):
                excel_model = sheet.cell(row, 0).value  # Cột Model (A)

                # Nếu import một model cụ thể, bỏ qua các model khác
                if model_name and excel_model != model_name:
                    continue

                # Tìm model trong database
                detail_model = self.env['detail.information'].search([('name', '=', excel_model)], limit=1)
                if not detail_model:
                    _logger.warning(f"Không tìm thấy model {excel_model} trong database")
                    continue

                # Xóa part list cũ nếu là record đầu tiên của model này
                if excel_model not in model_counts:
                    detail_model.part_list_ids.unlink()
                    model_counts[excel_model] = 0

                try:
                    # Tạo part list mới
                    self.env['part.list.information'].create({
                        'model_name': detail_model.id,
                        'no': int(sheet.cell(row, 1).value),  # Cột No (B)
                        'component_serial': sheet.cell(row, 2).value,  # Cột Component (C)
                        'description': sheet.cell(row, 3).value,  # Cột Description (D)
                        'quantity': 1  # Mặc định số lượng là 1
                    })
                    model_counts[excel_model] += 1

                except Exception as e:
                    _logger.error(f"Lỗi khi import dòng {row + 1}: {str(e)}")

            return model_counts

        except Exception as e:
            _logger.error(f"Lỗi khi đọc file Excel: {str(e)}")
            return {}

    def action_import_partlist(self):
        try:
            if self.import_type == 'single':
                # Import cho model hiện tại
                model_id = self.env.context.get('active_id')
                detail_model = self.env['detail.information'].browse(model_id)
                model_name = detail_model.name

                _logger.info(f"Import Part List cho model: {model_name}")
                model_counts = self.import_partlist_from_excel(self.excel_file, model_name)

                total_models = len(model_counts)
                total_records = sum(model_counts.values())

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