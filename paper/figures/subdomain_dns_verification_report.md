# Subdomain DNS Verification Report

Generated: 2026-08-07 05:19:10 +05:00

## Scope

- `Subdomains.csv`: semicolon-delimited hostname inventory.
- `api_methods.csv`: method, host, path endpoint inventory.
- Verification method: hostname syntax validation and passive DNS resolution via the local system resolver.
- No HTTP requests, port scans, vulnerability checks, authentication attempts, or traffic beyond DNS resolution were performed.

## Summary

- Unique hostnames checked: 413
- Valid hostname syntax: 411
- DNS-resolving hostnames: 212
- Valid but non-resolving hostnames: 199
- Invalid hostname syntax: 2
- Subdomains.csv resolving: 101 / 160
- api_methods.csv hosts resolving: 111 / 253

## Artifacts

- Raw subdomain inventory: `Subdomains.csv`
- Raw API host inventory: `api_methods.csv`
- Machine-readable verification table: `subdomain_dns_verification.csv`

## Invalid Hostname Syntax

| host | source | note |
|---|---|---|
| super_services.indrive.com | Subdomains.csv | invalid hostname syntax |
| super_services.indriver.com | Subdomains.csv | invalid hostname syntax |

## First Non-Resolving Hosts

| host | source | note |
|---|---|---|
| amga.console3.com | Subdomains.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| apple.indriver.com | Subdomains.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| auth-console.test.ams5.baremetal.indrive.tech | Subdomains.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| auth-ext-test.indrive.tech | Subdomains.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| baf-cf.euce1.indriverapp.com | api_methods.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| birthday.indrive.com | Subdomains.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| book.indriver.com | Subdomains.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| co-cf.sa.apso1.aws.indriverapp.com | api_methods.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| co-in-cf.africa.afso1.aws.indriverapp.com | api_methods.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| co-in-cf.cis.euce1.aws.indriverapp.com | api_methods.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| co-in-cf.eu.euce1.aws.indriverapp.com | api_methods.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| co-in-cf.latam.saea1.aws.indriverapp.com | api_methods.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| co-in-cf.latam-br.saea1.aws.indriverapp.com | api_methods.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| co-in-cf.latam-co.saea1.aws.indriverapp.com | api_methods.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| co-in-cf.latam-mx.usea1.aws.indriverapp.com | api_methods.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| co-in-cf.latam-pe.saea1.aws.indriverapp.com | api_methods.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| co-in-cf.sa.apso1.aws.indriverapp.com | api_methods.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| co-in-cf.sa-in.apso1.aws.indriverapp.com | api_methods.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| co-in-cf.sea.apse3.aws.indriverapp.com | api_methods.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |
| courier-cf.africa.afso1.aws.indriverapp.com | api_methods.csv | Exception calling "GetHostAddresses" with "1" argument(s): "No such host is known" |

## Interpretation Boundary

A resolving DNS record confirms that the hostname currently maps to at least one address. It does not confirm service ownership, application reachability, authorization scope, endpoint behavior, or security posture.
