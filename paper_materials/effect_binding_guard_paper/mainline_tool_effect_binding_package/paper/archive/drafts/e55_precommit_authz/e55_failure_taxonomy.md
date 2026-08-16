# E55 Failure Taxonomy

Failure example counts: `{'multi_resource_failure': 6, 'operation_failure': 6, 'alias_failure': 6, 'provenance_failure': 6, 'existing_false_allow': 6}`

- `multi_resource_failure` / `authz_aware_no_multi_resource_expansion` / `e55_email_00_02_34e56357`: expected `DENY`, predicted `ALLOW`.
- `operation_failure` / `authz_aware_no_operation_mode` / `e55_email_00_04_fc835495`: expected `DENY`, predicted `ALLOW`.
- `alias_failure` / `authz_aware_no_alias_resolution` / `e55_email_00_05_a3bc4096`: expected `ALLOW`, predicted `DENY`.
- `provenance_failure` / `authz_aware_no_provenance_overlay` / `e55_email_00_07_03358abe`: expected `DENY`, predicted `ALLOW`.
- `multi_resource_failure` / `authz_aware_no_multi_resource_expansion` / `e55_email_01_02_00674600`: expected `DENY`, predicted `ALLOW`.
- `operation_failure` / `authz_aware_no_operation_mode` / `e55_email_01_04_a429077f`: expected `DENY`, predicted `ALLOW`.
- `alias_failure` / `authz_aware_no_alias_resolution` / `e55_email_01_05_f2954f39`: expected `ALLOW`, predicted `DENY`.
- `provenance_failure` / `authz_aware_no_provenance_overlay` / `e55_email_01_07_56a40ee0`: expected `DENY`, predicted `ALLOW`.
- `multi_resource_failure` / `authz_aware_no_multi_resource_expansion` / `e55_email_02_02_b905437b`: expected `DENY`, predicted `ALLOW`.
- `operation_failure` / `authz_aware_no_operation_mode` / `e55_email_02_04_e3369a12`: expected `DENY`, predicted `ALLOW`.
- `alias_failure` / `authz_aware_no_alias_resolution` / `e55_email_02_05_b79ae4c4`: expected `ALLOW`, predicted `DENY`.
- `provenance_failure` / `authz_aware_no_provenance_overlay` / `e55_email_02_07_e0a457f2`: expected `DENY`, predicted `ALLOW`.
- `multi_resource_failure` / `authz_aware_no_multi_resource_expansion` / `e55_email_03_02_23e069ad`: expected `DENY`, predicted `ALLOW`.
- `operation_failure` / `authz_aware_no_operation_mode` / `e55_email_03_04_ec42d0b5`: expected `DENY`, predicted `ALLOW`.
- `alias_failure` / `authz_aware_no_alias_resolution` / `e55_email_03_05_00ae9972`: expected `ALLOW`, predicted `DENY`.
- `provenance_failure` / `authz_aware_no_provenance_overlay` / `e55_email_03_07_a0a24f1c`: expected `DENY`, predicted `ALLOW`.
- `multi_resource_failure` / `authz_aware_no_multi_resource_expansion` / `e55_email_04_02_2ee7874e`: expected `DENY`, predicted `ALLOW`.
- `operation_failure` / `authz_aware_no_operation_mode` / `e55_email_04_04_39057573`: expected `DENY`, predicted `ALLOW`.
- `alias_failure` / `authz_aware_no_alias_resolution` / `e55_email_04_05_e3d6b7c1`: expected `ALLOW`, predicted `DENY`.
- `provenance_failure` / `authz_aware_no_provenance_overlay` / `e55_email_04_07_c1fc1e12`: expected `DENY`, predicted `ALLOW`.
