# Runs Junie Bridge without interactive elevation for use by Scheduled Tasks
# Requires: Node.js on PATH
# This script is intended to be launched by a Scheduled Task set to "Run with highest privileges".
$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

# Start the bridge (server reads its own .env from junie-bridge/.env)
node .\junie-bridge\server.js
