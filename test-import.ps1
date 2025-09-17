
# Start the application in the background
Write-Host "Starting TahsilatApi server..."
Start-Process dotnet -ArgumentList "run" -WorkingDirectory "c:\D\tahsilat\TahsilatApi\TahsilatApi" -NoNewWindow

# Wait for the server to start
Write-Host "Waiting for server to start..."
Start-Sleep -Seconds 10

# Test if the server is running
try {
    $response = Invoke-WebRequest -Uri http://localhost:5000/swagger -UseBasicParsing -TimeoutSec 5
    Write-Host "Server is running successfully."

    # Test the file upload
    Write-Host "Testing file upload..."
    $boundary = [System.Guid]::NewGuid().ToString()
    $headers = @{
        "Content-Type" = "multipart/form-data; boundary=$boundary"
    }

    $fileContent = Get-Content -Raw "c:\D\tahsilat\test.csv"
    $body = @"
--$boundary
Content-Disposition: form-data; name="file"; filename="test.csv"
Content-Type: text/csv

$fileContent
--$boundary--
"@

    $uploadResponse = Invoke-RestMethod -Uri http://localhost:5000/api/Import/upload -Method POST -Headers $headers -Body $body
    Write-Host "Upload response: $($uploadResponse | ConvertTo-Json -Depth 3)"
}
catch {
    Write-Host "Error: $_"
}
finally {
    # Stop the server
    Write-Host "Stopping server..."
    Get-Process | Where-Object {$_.ProcessName -eq "dotnet"} | Stop-Process -Force
    Write-Host "Server stopped."
}
