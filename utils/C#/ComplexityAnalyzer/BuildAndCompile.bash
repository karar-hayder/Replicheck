@echo off
dotnet build
dotnet publish -c Release -r win-x64 --self-contained true /p:PublishSingleFile=true
