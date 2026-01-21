Get-ChildItem -Path ".\localdata\markdown_files" -Recurse -File |
    Sort-Object -Property Length -Descending |
    Select-Object -First 20 -Property Name, @{Name="Size (GB)";Expression={[Math]::Round($_.Length/1GB,2)}}, FullName |
    Format-Table -AutoSize
