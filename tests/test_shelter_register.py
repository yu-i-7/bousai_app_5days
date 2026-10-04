import unittest

from app import app, parse_area_warnings


class ShelterRegisterRouteTest(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session['logged_in'] = True
            session['username'] = 'admin'

    def test_register_shelter_accepts_post(self):
        response = self.client.post('/shelter_register', data={'name': '新しい避難所'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('新しい避難所', response.get_data(as_text=True))

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
