$files = Get-ChildItem -Path ".\localdata\markdown_files" -Recurse -File -Filter "part-*.parquet.csv"
$totalSize = ($files | Measure-Object -Property Length -Sum).Sum

Write-Host "Всего part-файлов: $($files.Count)"
Write-Host "Общий размер: $([Math]::Round($totalSize/1GB,2)) ГБ"
Write-Host ""

# Группировка по директориям
$grouped = $files | Group-Object -Property DirectoryName
Write-Host "Распределение по папкам:"
foreach ($group in $grouped) {
    $dirSize = ($group.Group | Measure-Object -Property Length -Sum).Sum
    $dirName = Split-Path $group.Name -Leaf
    Write-Host "  $dirName : $($group.Count) файлов, $([Math]::Round($dirSize/1GB,2)) ГБ"
}
