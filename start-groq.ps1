$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$grandSecret = Read-Host 'Введите API-ключ Groq (ввод скрыт)' -AsSecureString
$grandPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($grandSecret)
try {
    $env:GROQ_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($grandPointer)
    $env:COPILOT_PROVIDER = 'groq'
    $env:GROQ_MODEL = 'openai/gpt-oss-120b'
    $env:GROQ_INPUT_USD_PER_M = '0.15'
    $env:GROQ_OUTPUT_USD_PER_M = '0.60'
    Write-Host 'Groq включён. Ключ хранится в памяти этого процесса, в файлы не записывается.'
    python -m copilot.server
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($grandPointer)
    Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:COPILOT_PROVIDER -ErrorAction SilentlyContinue
    $grandSecret.Dispose()
}
