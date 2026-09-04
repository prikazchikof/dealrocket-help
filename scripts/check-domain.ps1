$ErrorActionPreference = 'Stop'

$domain = 'help.dealrocket.ru'
$expectedTarget = 'prikazchikof.github.io'
$expectedCanonical = 'https://help.dealrocket.ru/'
$errors = [System.Collections.Generic.List[string]]::new()

try {
	$cname = Resolve-DnsName -Name $domain -Type CNAME -ErrorAction Stop |
		Where-Object { $_.Type -eq 'CNAME' } |
		Select-Object -First 1

	if (-not $cname -or $cname.NameHost.TrimEnd('.').ToLowerInvariant() -ne $expectedTarget) {
		$actual = if ($cname) { $cname.NameHost } else { '<missing CNAME>' }
		$errors.Add("CNAME: expected $expectedTarget, got $actual")
	} else {
		Write-Host "OK CNAME: $domain -> $($cname.NameHost)"
	}
} catch {
	$errors.Add("CNAME for $domain was not found")
}

try {
	$homeResponse = Invoke-WebRequest -Uri $expectedCanonical -MaximumRedirection 5 -UseBasicParsing
	if ($homeResponse.StatusCode -ne 200) {
		$errors.Add("Homepage returned HTTP $($homeResponse.StatusCode)")
	} elseif ($homeResponse.Content -notmatch '<link rel="canonical" href="https://help\.dealrocket\.ru/">') {
		$errors.Add('Custom-domain canonical URL was not found on the homepage')
	} else {
		Write-Host 'OK HTTPS and canonical'
	}
} catch {
	$errors.Add("HTTPS is unavailable: $($_.Exception.Message)")
}

try {
	$corpus = Invoke-RestMethod -Uri "https://$domain/assets/help-corpus.v1.json"
	if ($corpus.schema_version -ne 1 -or $corpus.articles.Count -lt 1) {
		$errors.Add('Help corpus is empty or has the wrong schema')
	} else {
		Write-Host "OK corpus: $($corpus.articles.Count) articles"
	}
} catch {
	$errors.Add("Help corpus is unavailable: $($_.Exception.Message)")
}

$deepLinks = [ordered]@{
	'/data-quality/' = @('sources')
	'/search/company-list/' = @('enrichment')
	'/search/refine/' = @()
	'/billing/' = @('invoicebox', 'documents', 'refund', 'cancellation')
	'/export/' = @('all-or-selected', 'stars', 'empty-fields', 'over-10000')
}

foreach ($path in $deepLinks.Keys) {
	try {
		$article = Invoke-WebRequest -Uri "https://$domain$path" -MaximumRedirection 5 -UseBasicParsing
		if ($article.StatusCode -ne 200) {
			$errors.Add("$path returned HTTP $($article.StatusCode)")
			continue
		}

		foreach ($anchor in $deepLinks[$path]) {
			if ($article.Content -notmatch ('id=["'']' + [regex]::Escape($anchor) + '["'']')) {
				$errors.Add("$path#$anchor was not found")
			}
		}
		Write-Host "OK article: $path"
	} catch {
		$errors.Add("$path is unavailable: $($_.Exception.Message)")
	}
}

if ($errors.Count -gt 0) {
	Write-Error ("Custom domain is not ready:`n- " + ($errors -join "`n- "))
}

Write-Host 'help.dealrocket.ru is ready for the frontend cutover.'
