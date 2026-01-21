Get-ChildItem -Path ".\localdata\markdown_files" -Recurse -File -Filter "part-*.parquet.csv" |
    Sort-Object -Property Length -Descending |
    Select-Object -First 10 -Property Name, @{Name="Size (GB)";Expression={[Math]::Round($_.Length/1GB,2)}}, DirectoryName |
    Format-List
