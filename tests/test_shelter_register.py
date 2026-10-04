import unittest
from unittest.mock import patch

import app as app_module
from app import app, parse_area_warnings


class ShelterRegisterRouteTest(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'admin'

    def test_register_shelter_accepts_post(self):
        saved_shelters = list(app_module.shelters)
        try:
            with patch.object(app_module, 'save_shelters'):
                response = self.client.post('/shelter_register', data={
                    'name': '新しい避難所',
                    'address': '青森市中央一丁目',
                    'capacity': '250',
                    'disasters': ['津波', '土砂災害'],
                    'facilities': ['ペット可', 'バリアフリー'],
                    'status': '開設中',
                })
            self.assertEqual(response.status_code, 200)
            self.assertIn('新しい避難所', response.get_data(as_text=True))
            registered = app_module.shelters[-1]
            self.assertEqual(registered['address'], '青森市中央一丁目')
            self.assertEqual(registered['capacity'], 250)
            self.assertEqual(registered['disasters'], ['津波', '土砂災害'])
            self.assertEqual(registered['facilities'], ['ペット可', 'バリアフリー'])
            self.assertEqual(registered['status'], '開設中')
        finally:
            app_module.shelters[:] = saved_shelters

    def test_shelter_registration_page_renders_required_controls(self):
        response = self.client.get('/shelter_register')
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        for expected in (
            'name="name"',
            'name="address"',
            'name="capacity"',
            'name="disasters"',
            '津波',
            'name="facilities"',
            'ペット可',
            'name="status"',
            '入力内容を確認してください',
            '編集',
        ):
            self.assertIn(expected, page)

    def test_shelter_registration_rejects_missing_fields_and_non_numeric_capacity(self):
        with patch.object(app_module, 'save_shelters'):
            missing_response = self.client.post('/shelter_register', data={
                'name': '青森避難所',
                'address': '',
                'capacity': '120',
            })
            invalid_response = self.client.post('/shelter_register', data={
                'name': '青森避難所',
                'address': '青森市中央一丁目',
                'capacity': '12a',
            })
            unicode_digit_response = self.client.post('/shelter_register', data={
                'name': '青森避難所',
                'address': '青森市中央一丁目',
                'capacity': '12²',
            })
        self.assertIn('住所を入力してください', missing_response.get_data(as_text=True))
        self.assertIn('収容人数は1以上の数字で入力してください', invalid_response.get_data(as_text=True))
        self.assertIn('収容人数は1以上の数字で入力してください', unicode_digit_response.get_data(as_text=True))

    def test_shelter_registration_edits_existing_record(self):
        saved_shelters = list(app_module.shelters)
        app_module.shelters[:] = [{
            'id': 91,
            'name': '更新前の避難所',
            'address': '青森市内',
            'capacity': 50,
            'disasters': ['津波'],
            'facilities': [],
            'status': '閉鎖中',
        }]
        try:
            with patch.object(app_module, 'save_shelters'):
                response = self.client.post('/shelter_register', data={
                    'shelter_id': '91',
                    'name': '更新後の避難所',
                    'address': '青森市新町一丁目',
                    'capacity': '180',
                    'disasters': ['洪水'],
                    'facilities': ['バリアフリー'],
                    'status': '開設中',
                })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(app_module.shelters), 1)
            self.assertEqual(app_module.shelters[0]['name'], '更新後の避難所')
            self.assertEqual(app_module.shelters[0]['capacity'], 180)
        finally:
            app_module.shelters[:] = saved_shelters

    def test_board_registers_new_instruction(self):
        response = self.client.post('/board', data={
            'content': '避難指示を発令します',
            'target': '住民',
            'shelter': '青森市役所',
            'recipient': '住民向け',
            'target_area': '青森市',
            'priority': '高'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('避難指示を発令します', response.get_data(as_text=True))
        self.assertIn('住民向け', response.get_data(as_text=True))

    def test_board_updates_instruction_status(self):
        response = self.client.post('/board/status/1', data={'status': '対応中'})
        self.assertEqual(response.status_code, 302)

    def test_board_accepts_broadcast_message(self):
        response = self.client.post('/board', data={
            'broadcast_content': '避難所への進入はご遠慮ください',
            'broadcast_target': '住民向け',
            'broadcast_area': '青森市',
            'display_on_home': 'on'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('避難所への進入はご遠慮ください', response.get_data(as_text=True))

    def test_broadcast_home_display_checkbox_controls_home_notice(self):
        saved_broadcasts = list(app_module.broadcasts)
        try:
            with patch.object(app_module, 'save_broadcasts'):
                self.client.post('/board', data={
                    'broadcast_content': 'ホーム表示する確認用のお知らせ',
                    'broadcast_area': '青森市',
                    'display_on_home': 'on'
                })
                home_response = self.client.get('/')
                self.assertIn('ホーム表示する確認用のお知らせ', home_response.get_data(as_text=True))

                self.client.post('/board', data={
                    'broadcast_content': 'ホーム表示しない確認用のお知らせ',
                    'broadcast_area': '青森市'
                })
                hidden_home_response = self.client.get('/')
                self.assertNotIn('ホーム表示しない確認用のお知らせ', hidden_home_response.get_data(as_text=True))
        finally:
            app_module.broadcasts[:] = saved_broadcasts

    def test_parse_area_warnings_handles_aomori_city_code(self):
        sample = [{
            'reportDatetime': '2026-10-04T08:00:00+09:00',
            'warning': {
                'class20Items': [{
                    'areaCode': '0220100',
                    'kinds': [{'code': '10', 'status': '発表'}]
                }]
            }
        }]

        warnings, report_datetime = parse_area_warnings(sample)
        self.assertEqual(report_datetime, '2026-10-04T08:00:00+09:00')
        self.assertEqual(warnings[0]['code'], '10')
        self.assertEqual(warnings[0]['name'], 'レベル2大雨注意報')


if __name__ == '__main__':
    unittest.main()
