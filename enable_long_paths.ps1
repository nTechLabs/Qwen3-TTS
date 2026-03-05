# Windows Long Path 활성화 스크립트
# 관리자 권한으로 실행 필요

Write-Host "Windows Long Path 지원 활성화 중..." -ForegroundColor Yellow

# 레지스트리 설정
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem"
Set-ItemProperty -Path $regPath -Name "LongPathsEnabled" -Value 1 -Type DWord

Write-Host "✓ Long Path 지원이 활성화되었습니다." -ForegroundColor Green
Write-Host "재부팅 후 적용됩니다." -ForegroundColor Cyan
Write-Host ""
Write-Host "활성화 후 flash-attn 설치:" -ForegroundColor Yellow
Write-Host "  .\.venv\Scripts\python.exe -m pip install flash-attn --no-build-isolation" -ForegroundColor White
