Start-Process -Verb RunAs powershell -ArgumentList @"
cd C:\Users\benny\IdeaProjects\agent-factory
node .\junie-bridge\server.js
"@ 
