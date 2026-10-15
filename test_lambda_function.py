import unittest
from unittest.mock import Mock

import lambda_function


USER_POOL_ID = "ap-southeast-1_example"


class CognitoStudentIdHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_pool = lambda_function.os.environ.get("USER_POOL_ID")
        lambda_function.os.environ["USER_POOL_ID"] = USER_POOL_ID

    def tearDown(self) -> None:
        if self._previous_pool is None:
            lambda_function.os.environ.pop("USER_POOL_ID", None)
        else:
            lambda_function.os.environ["USER_POOL_ID"] = self._previous_pool

    def test_sets_student_id_using_username_when_both_keys_are_present(self) -> None:
        cognito = Mock()

        result = lambda_function.lambda_handler(
            {
                "username": "verified-user",
                "sub": "verified-sub",
                "student_id": "2026123456",
            },
            None,
            cognito,
        )

        self.assertEqual(result, {"statusCode": 200, "updated": True})
        cognito.admin_update_user_attributes.assert_called_once_with(
            UserPoolId=USER_POOL_ID,
            Username="verified-user",
            UserAttributes=[{"Name": "custom:student_id", "Value": "2026123456"}],
        )

    def test_uses_sub_when_username_is_absent(self) -> None:
        cognito = Mock()

        result = lambda_function.lambda_handler(
            {"sub": "verified-sub", "student_id": " 2026123456 "},
            None,
            cognito,
        )

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(
            cognito.admin_update_user_attributes.call_args.kwargs["Username"],
            "verified-sub",
        )
        self.assertEqual(
            cognito.admin_update_user_attributes.call_args.kwargs["UserAttributes"][0]["Value"],
            "2026123456",
        )

    def test_missing_fields_return_400_without_calling_cognito(self) -> None:
        cognito = Mock()
        cases = [
            {},
            {"username": "verified-user"},
            {"student_id": "2026123456"},
            {"username": "  ", "sub": "", "student_id": "2026123456"},
            {"username": "verified-user", "student_id": "   "},
            {"username": 12, "student_id": "2026123456"},
            None,
        ]

        for event in cases:
            with self.subTest(event=event):
                result = lambda_function.lambda_handler(event, None, cognito)
                self.assertEqual(result["statusCode"], 400)

        cognito.admin_update_user_attributes.assert_not_called()

    def test_repeating_the_same_value_is_success(self) -> None:
        cognito = Mock()
        event = {"username": "verified-user", "student_id": "2026123456"}

        first = lambda_function.lambda_handler(event, None, cognito)
        second = lambda_function.lambda_handler(event, None, cognito)

        self.assertEqual(first, {"statusCode": 200, "updated": True})
        self.assertEqual(second, {"statusCode": 200, "updated": True})
        self.assertEqual(cognito.admin_update_user_attributes.call_count, 2)

    def test_an_unchanged_attribute_error_does_not_raise(self) -> None:
        cognito = Mock()
        cognito.admin_update_user_attributes.side_effect = _unchanged_error()

        result = lambda_function.lambda_handler(
            {"username": "verified-user", "student_id": "2026123456"},
            None,
            cognito,
        )

        self.assertEqual(result, {"statusCode": 200, "unchanged": True})

    def test_missing_user_pool_returns_500_without_calling_cognito(self) -> None:
        lambda_function.os.environ["USER_POOL_ID"] = "  "
        cognito = Mock()

        result = lambda_function.lambda_handler(
            {"username": "verified-user", "student_id": "2026123456"},
            None,
            cognito,
        )

        self.assertEqual(result, {"statusCode": 500, "error": "USER_POOL_ID is not configured"})
        cognito.admin_update_user_attributes.assert_not_called()


def _unchanged_error() -> Exception:
    error = Exception("An error occurred (InvalidParameterException) when calling AdminUpdateUserAttributes: Attribute unchanged")
    error.response = {  # type: ignore[attr-defined]
        "Error": {
            "Code": "InvalidParameterException",
            "Message": "Attribute unchanged",
        }
    }
    return error


if __name__ == "__main__":
    unittest.main()
