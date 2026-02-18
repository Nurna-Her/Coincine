Write-Host "Starting Coincine..."

# Start Backend
Write-Host "Starting Backend Server..."
# Start the backend process in a new window so it doesn't block this shell and stays alive
Start-Process -FilePath "python" -ArgumentList "-m uvicorn backend.app.main:app --reload"

# Wait for server to initialize
Start-Sleep -Seconds 3

# Open Frontend
Write-Host "Launching Frontend..."
# Opens the HTML file in the default browser
Start-Process "frontend\index.html"

Write-Host "App is up and running!"
