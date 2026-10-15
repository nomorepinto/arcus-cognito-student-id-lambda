# Arcus Cognito student ID sync

Python 3.12 Lambda. Arcus Attendance calls it asynchronously after a new student registration. The function writes that student number onto the caller's Cognito user as `custom:student_id`.

The user pool must already define `custom:student_id` and include it in the access token, the same way `custom:organization_id` is included. This package does not create the attribute.

## Invoke payload

Arcus Attendance sends this JSON (`InvocationType: Event`):

```json
{
  "username": "verified-user",
  "sub": "11111111-2222-3333-4444-555555555555",
  "student_id": "2026123456"
}
```

`username` is used when it is present. `sub` is used only when `username` is missing. A missing `student_id`, or a missing user key, returns `400` and does not call Cognito. Setting the attribute again, including an "attribute unchanged" response, returns `200`.

## Environment

| Variable | Required | Purpose |
| --- | --- | --- |
| `USER_POOL_ID` | yes | Arcus Cognito user pool id |
| `AWS_REGION` | set by Lambda | Defaults to `ap-southeast-1` when unset |

Execution role: `cognito-idp:AdminUpdateUserAttributes` on that user pool only. Arcus Attendance's server role needs `lambda:InvokeFunction` on this function. Set `STUDENT_ID_SYNC_LAMBDA_NAME` on attendance to the function name or ARN.

## Local test

```powershell
python -m unittest test_lambda_function.py
```

## Deploy

From this directory. Replace the account id and role ARN before the first create.

```powershell
python -c "import zipfile; z=zipfile.ZipFile('function.zip','w'); z.write('lambda_function.py'); z.close()"

aws lambda create-function --function-name arcus-cognito-student-id --runtime python3.12 --role arn:aws:iam::ACCOUNT_ID:role/arcus-cognito-student-id --handler lambda_function.lambda_handler --zip-file fileb://function.zip --region ap-southeast-1 --environment "Variables={USER_POOL_ID=ap-southeast-1_POOLID}" --timeout 10
```

Update code after the function exists:

```powershell
python -c "import zipfile; z=zipfile.ZipFile('function.zip','w'); z.write('lambda_function.py'); z.close()"

aws lambda update-function-code --function-name arcus-cognito-student-id --zip-file fileb://function.zip --region ap-southeast-1
```
