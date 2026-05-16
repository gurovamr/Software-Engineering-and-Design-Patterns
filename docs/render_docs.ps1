$ErrorActionPreference = "Stop"

$docsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pumlPath = Join-Path $docsDir "uml_description.puml"
$outputDir = Join-Path $docsDir "generated"
$relativeOutput = "generated"

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$quartoCommand = Get-Command quarto -ErrorAction SilentlyContinue
if (-not $quartoCommand) {
    throw "Quarto was not found on PATH. Install Quarto to render class_overview.md."
}

Push-Location $docsDir
try {
    & $quartoCommand.Source render class_overview.md `
        --to html `
        --output-dir generated `
        --output class_overview.html `
        --embed-resources
} finally {
    Pop-Location
}

$quartoGitignore = Join-Path $docsDir ".gitignore"
if (Test-Path $quartoGitignore) {
    Remove-Item -LiteralPath $quartoGitignore -Force
}

Get-ChildItem -Path $outputDir -File |
    Where-Object {
        $_.Name -like "uml_*.png" -or
        $_.Name -like "uml_*.svg" -or
        $_.Name -eq "uml_description_view.html"
    } |
    Remove-Item -Force

$plantumlCommand = Get-Command plantuml -ErrorAction SilentlyContinue
$plantumlJar = Get-ChildItem `
    -Path (Join-Path $env:USERPROFILE ".vscode\extensions") `
    -Recurse `
    -Filter "plantuml.jar" `
    -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending |
    Select-Object -First 1

if ($plantumlCommand) {
    & $plantumlCommand.Source -tpng -o $relativeOutput $pumlPath
} elseif ($plantumlJar) {
    & java -jar $plantumlJar.FullName -tpng -o $relativeOutput $pumlPath
} else {
    throw "PlantUML was not found on PATH and no VS Code PlantUML extension jar was found."
}

$diagrams = @(
    @{
        File = "uml_architecture_overview.png"
        Title = "Architecture Overview"
        Description = "Layer-level runtime flow and the meaning of each cross-layer dependency."
    },
    @{
        File = "uml_description.png"
        Title = "Detailed UML Description"
        Description = "Detailed class-style diagram with the main application, service, repository, FastF1, DTO, and visualization classes."
    },
    @{
        File = "uml_component_map.png"
        Title = "Full Component Map"
        Description = "All current application, service, repository, FastF1, DTO, and visualization components grouped by layer."
    },
    @{
        File = "uml_session_loading.png"
        Title = "DB-First Session Loading"
        Description = "How SessionService, SQLite repositories, FastF1, and DTOs cooperate."
    },
    @{
        File = "uml_dash_lap_logic.png"
        Title = "Dash Lap Logic"
        Description = "How driver selection, lap tables, telemetry plots, and track maps are connected."
    }
)

$availableDiagrams = foreach ($diagram in $diagrams) {
    if (Test-Path (Join-Path $outputDir $diagram.File)) {
        $diagram
    }
}

if (-not $availableDiagrams) {
    $availableDiagrams = Get-ChildItem -Path $outputDir -Filter "*.png" |
        Sort-Object Name |
        ForEach-Object {
            @{
                File = $_.Name
                Title = $_.BaseName
                Description = "Generated UML diagram."
            }
        }
}

$diagramHtml = ($availableDiagrams | ForEach-Object {
    @"
    <section>
      <h2>$($_.Title)</h2>
      <p>$($_.Description)</p>
      <img src="$($_.File)" alt="$($_.Title)">
    </section>
"@
}) -join "`n"

$viewHtml = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>F1 Telemetry Dashboard UML</title>
  <style>
    body { margin: 0; background: #111; color: #eee; font-family: Arial, sans-serif; }
    header { padding: 12px 16px; background: #1f1f1f; border-bottom: 1px solid #333; }
    main { padding: 16px; overflow: auto; }
    section { margin: 0 0 28px; }
    h2 { margin: 0 0 4px; font-size: 18px; }
    p { margin: 0 0 12px; color: #bbb; }
    img { background: white; max-width: none; border: 1px solid #333; }
  </style>
</head>
<body>
  <header>F1 Telemetry Dashboard UML</header>
  <main>
$diagramHtml
  </main>
</body>
</html>
"@

Set-Content -Path (Join-Path $outputDir "uml_description_view.html") -Value $viewHtml

Write-Host "Generated:"
Write-Host "  docs/generated/class_overview.html"
foreach ($diagram in $availableDiagrams) {
    Write-Host "  docs/generated/$($diagram.File)"
}
Write-Host "  docs/generated/uml_description_view.html"
