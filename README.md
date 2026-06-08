# DevOps - CloudFormation và CodePipeline để quản lý và triển khai hạ tầng AWS
Hướng dẫn triển khai hạ tầng AWS bằng CloudFormation kết hợp CI/CD tự động với AWS CodePipeline cho bài thực hành 02.

## Điều Kiện Và Cách Chuẩn Bị

### 1. AWS CLI
Kiểm tra AWS CLI:
```powershell
aws --version
```
Nếu chưa có, cài bằng:
```powershell
winget install Amazon.AWSCLI
```
Nếu cài xong nhưng PowerShell chưa nhận lệnh `aws`, đóng PowerShell và mở lại. Nếu vẫn chưa nhận, thêm AWS CLI vào `PATH` tạm thời:
```powershell
$env:Path += ";C:\Program Files\Amazon\AWSCLIV2"
aws --version
```

### 2. AWS Credentials
Nếu dùng AWS Academy/VocLabs, vào `Cloud Access`, bấm `Show` ở mục `AWS CLI`, rồi copy block có dạng:
```ini
[default]
aws_access_key_id=...
aws_secret_access_key=...
aws_session_token=...
```
Tạo thư mục `.aws` và lưu credentials:
```powershell
New-Item -ItemType Directory -Force $env:USERPROFILE\.aws
notepad "$env:USERPROFILE\.aws\credentials"
```
Dán block credentials vào file trên. Khi lưu, chọn **Save as type: All Files** và đặt tên file là `credentials` (không có đuôi `.txt`). Tiếp theo tạo file cấu hình region:
```powershell
notepad "$env:USERPROFILE\.aws\config"
```
Dán nội dung sau, thay `us-east-1` bằng region đang dùng nếu khác:
```ini
[default]
region=us-east-1
output=json
```
Lưu tương tự với **Save as type: All Files**, tên file là `config`. Kiểm tra credentials:
```powershell
aws sts get-caller-identity
```

### 3. EC2 Key Pair
Trong AWS Console, chọn đúng region sẽ deploy, sau đó vào:
```text
EC2 -> Key pairs -> Create key pair
```
Tạo key pair với thông tin ví dụ:
```text
Name: devops-lab-key
Key pair type: RSA
Private key file format: .pem
```
Lưu file `.pem` ở một thư mục riêng. Nếu dùng tên key pair khác, cập nhật lại tham số `KeyName` ở bước deploy bên dưới.

Hoặc tạo key pair bằng AWS CLI:
```powershell
aws ec2 create-key-pair `
  --key-name devops-lab-key `
  --query "KeyMaterial" `
  --output text `
  --region us-east-1 > "$env:USERPROFILE\devops-lab-key.pem"
```

### 4. git-remote-codecommit
Công cụ này cho phép dùng `git` với CodeCommit thông qua AWS credentials:
```powershell
pip install git-remote-codecommit
```
Kiểm tra:
```powershell
git remote --version
```

## Triển Khai Pipeline

Pipeline được định nghĩa hoàn toàn bằng CloudFormation trong file `pipeline/codepipeline.yaml`. Một lệnh deploy duy nhất sẽ tạo ra toàn bộ hệ thống CI/CD gồm: CodeCommit repository, S3 artifact bucket, IAM roles, CodeBuild projects và CodePipeline.

### Bước 1: Lấy IP public hiện tại
```powershell
curl.exe https://checkip.amazonaws.com
```
Nếu IP public là `x.x.x.x`, sử dụng `x.x.x.x/32` cho tham số `AllowedSshCidr` bên dưới.

### Bước 2: Deploy pipeline stack
Thay `<cidr-duoc-phep-ssh>` và `<ten-key-pair>` theo môi trường của bạn:
```powershell
cd <duong-dan-repo>

aws cloudformation deploy `
  --template-file pipeline/codepipeline.yaml `
  --stack-name devops-lab02-pipeline `
  --parameter-overrides `
    AllowedSshCidr="<cidr-duoc-phep-ssh>" `
    KeyName="<ten-key-pair>" `
    AvailabilityZone="us-east-1a" `
  --capabilities CAPABILITY_IAM `
  --region us-east-1
```
Lệnh này mất khoảng 2-3 phút. Khi thấy `Successfully created/updated stack` là hoàn tất.

### Bước 3: Lấy URL CodeCommit từ stack output
```powershell
aws cloudformation describe-stacks `
  --stack-name devops-lab02-pipeline `
  --query "Stacks[0].Outputs" `
  --output table `
  --region us-east-1
```
Ghi lại giá trị `RepositoryCloneUrlHttp` từ kết quả trên.

### Bước 4: Push code lên CodeCommit
Thêm CodeCommit làm remote và push code:
```powershell
git remote add codecommit codecommit::us-east-1://devops-lab02-cloudformation-codepipeline

git push codecommit main
```
Sau khi push, CodePipeline tự động kích hoạt. Có thể trigger thủ công nếu cần:
```powershell
aws codepipeline start-pipeline-execution `
  --name devops-lab02-cloudformation-pipeline `
  --region us-east-1
```

## Kiểm Tra Pipeline

Theo dõi trạng thái các stage của pipeline:
```powershell
aws codepipeline get-pipeline-state `
  --name devops-lab02-cloudformation-pipeline `
  --region us-east-1 `
  --query "stageStates[*].{Stage:stageName,Status:latestExecution.status}" `
  --output table
```
Pipeline gồm 3 stage:
- **Source**: Lấy mã nguồn từ CodeCommit.
- **Validate**: Chạy cfn-lint kiểm tra syntax templates và Taskcat test deploy thực tế.
- **Deploy**: Đóng gói nested stacks và deploy hạ tầng lên AWS.

Stage Validate mất khoảng 10-15 phút do Taskcat tạo và xóa hạ tầng test thật trên AWS.

## Xem Kết Quả Sau Khi Deploy

Sau khi stage Deploy hoàn tất, xem output của hạ tầng được tạo:
```powershell
aws cloudformation describe-stacks `
  --stack-name devops-lab02-infrastructure `
  --query "Stacks[0].Outputs" `
  --output table `
  --region us-east-1
```
Output bao gồm: VPC ID, Public EC2 ID, Public IP, Private EC2 ID, Private IP.

SSH vào Public EC2:
```powershell
ssh -i <duong-dan-file-pem> ec2-user@<PublicInstancePublicIp>
```
Copy private key lên Public EC2:
```powershell
scp -i <duong-dan-file-pem> <duong-dan-file-pem> ec2-user@<PublicInstancePublicIp>:/home/ec2-user/devops-lab-key.pem
```
Từ Public EC2, SSH vào Private EC2:
```bash
chmod 400 devops-lab-key.pem
ssh -i devops-lab-key.pem ec2-user@<PrivateInstancePrivateIp>
```

## Cập Nhật Pipeline Khi Cần Thay Đổi Cấu Hình

Nếu cần thay đổi IAM permissions hoặc cấu hình CodeBuild/CodePipeline, chỉnh sửa `pipeline/codepipeline.yaml` rồi chạy lại lệnh deploy ở Bước 2. CloudFormation sẽ tự động phát hiện và cập nhật chỉ những thành phần thay đổi.

## Xóa Tài Nguyên Sau Khi Demo

Xóa theo thứ tự: xóa hạ tầng trước, sau đó mới xóa pipeline.

Xóa hạ tầng đã deploy:
```powershell
aws cloudformation delete-stack `
  --stack-name devops-lab02-infrastructure `
  --region us-east-1
```
Chờ stack hạ tầng xóa xong (khoảng 5-10 phút):
```powershell
aws cloudformation wait stack-delete-complete `
  --stack-name devops-lab02-infrastructure `
  --region us-east-1
```
Xóa S3 bucket artifacts (bắt buộc phải xóa trước khi xóa pipeline stack):
```powershell
$bucket = aws cloudformation describe-stacks `
  --stack-name devops-lab02-pipeline `
  --query "Stacks[0].Outputs[?OutputKey=='ArtifactBucketName'].OutputValue" `
  --output text `
  --region us-east-1

aws s3 rb "s3://$bucket" --force --region us-east-1
```
Xóa pipeline stack:
```powershell
aws cloudformation delete-stack `
  --stack-name devops-lab02-pipeline `
  --region us-east-1
```

> **Lưu ý chi phí**: NAT Gateway tốn khoảng $0.045/giờ. Nhớ xóa tài nguyên ngay sau khi demo xong để tránh phát sinh chi phí.
