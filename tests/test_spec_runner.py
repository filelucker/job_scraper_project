import unittest
from unittest.mock import MagicMock, patch
from tools.spec_runner import SpecRunner, extract_json_path

class TestSpecRunner(unittest.TestCase):
    def test_extract_json_path(self):
        data = {
            "data": {
                "jobBoard": {
                    "jobPostings": [
                        {"id": "job_1", "title": "Senior Engineer"},
                        {"id": "job_2", "title": "Staff Engineer"}
                    ]
                }
            }
        }
        res = extract_json_path(data, "data.jobBoard.jobPostings")
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]["id"], "job_1")

        # Specific index
        item = extract_json_path(data, "data.jobBoard.jobPostings[1]")
        self.assertEqual(item["title"], "Staff Engineer")

    def test_spec_runner_ashby_spec_execution(self):
        sample_spec = {
            "name": "ashby",
            "operations": [
                {
                    "name": "listJobs",
                    "request": {
                        "method": "POST",
                        "url": "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams",
                        "headers": {
                            "content-type": "application/json",
                            "referer": "https://jobs.ashbyhq.com/{company}"
                        },
                        "body": '{"variables":{"organizationHostedJobsPageName":"{company}"}}'
                    },
                    "slots": [
                        {
                            "param": "company",
                            "at": ["header:referer"],
                            "template": "https://jobs.ashbyhq.com/{company}"
                        }
                    ],
                    "response": {
                        "format": "json",
                        "extract": "data.jobBoard.jobPostings"
                    }
                }
            ]
        }

        runner = SpecRunner(sample_spec)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "jobBoard": {
                    "jobPostings": [
                        {"id": "ashby_101", "title": "Flutter Developer"}
                    ]
                }
            }
        }

        with patch("requests.Session.request", return_value=mock_response) as mock_req:
            result = runner.execute("listJobs", params={"company": "monzo"})

            self.assertEqual(result["status"], 200)
            self.assertEqual(len(result["data"]), 1)
            self.assertEqual(result["data"][0]["title"], "Flutter Developer")

            mock_req.assert_called_once()
            called_kwargs = mock_req.call_args[1]
            self.assertEqual(called_kwargs["headers"]["referer"], "https://jobs.ashbyhq.com/monzo")
            self.assertIn('"organizationHostedJobsPageName":"monzo"', called_kwargs["data"].decode("utf-8"))

    def test_spec_runner_cookie_slots(self):
        sample_spec = {
            "name": "linkedin",
            "operations": [
                {
                    "name": "getMe",
                    "request": {
                        "method": "GET",
                        "url": "https://www.linkedin.com/voyager/api/me",
                        "headers": {
                            "csrf-token": ""
                        }
                    },
                    "slots": [
                        {
                            "ref": "cookie:JSESSIONID",
                            "at": ["header:csrf-token"],
                            "transform": "strip-quotes"
                        }
                    ],
                    "response": {
                        "format": "json"
                    }
                }
            ]
        }

        runner = SpecRunner(sample_spec)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "test_user"}

        with patch("requests.Session.request", return_value=mock_response) as mock_req:
            cookies = {"JSESSIONID": '"ajax:12345"'}
            result = runner.execute("getMe", cookies=cookies)

            self.assertEqual(result["status"], 200)
            called_headers = mock_req.call_args[1]["headers"]
            self.assertEqual(called_headers["csrf-token"], "ajax:12345")

if __name__ == "__main__":
    unittest.main()

