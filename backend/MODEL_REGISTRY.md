# Model registry and deployment

## Architecture currently in this repository

The API is Flask. `/predict` and `/predict-batch` serve Upstream models through
`predict.Predictor`; `/formulation-predict` and its batch route serve Formulation
models through `FormulationPredictor`. Both originally loaded local
scikit-learn/joblib artifacts at process startup. The old `/retrain` routes
trained synchronously and overwrote those files. There was no database,
authentication, object storage, or queue configuration in the repository.
Downstream has no prediction, training, schema, or artifact implementation, so
it is not included in this registry rollout.

The registry adds Postgres metadata, private R2 dataset/model artifacts, Redis
Queue jobs, Supabase access-token verification, and a refreshable in-memory
model overlay. Existing local artifacts remain a fallback. A model is generated
inside the training worker, stored as a candidate, evaluated against the current
active model (or local legacy model), and only becomes active after an
administrator explicitly promotes it. API instances poll the active pointer
every `MODEL_REGISTRY_REFRESH_SECONDS`; promotion also refreshes the instance
that handled the request.

Uploads are considered eligible training data only after schema and numeric
validation. Training combines valid datasets from the same Supabase tenant
uploaded no later than the selected dataset, deduplicates rows, and records the
dataset lineage. A candidate is marked promotion-eligible only when its holdout
R² matches or exceeds the incumbent on the same holdout data. The additional
`MODEL_MIN_TEST_R2` threshold defaults to `-1`.

Joblib artifacts are never accepted from browser uploads. Registry artifacts
are written only by the trusted worker using server-generated estimators,
remain in a private bucket, and are checksum/schema-validated before promotion,
local synchronization, and activation. Pickle-based formats are executable
serialization formats; do not permit direct artifact uploads or grant users
write access to the bucket/database.

## Required infrastructure

Provision:

1. Render PostgreSQL.
2. Render Key Value/Redis.
3. A private Supabase Storage bucket with S3 access enabled.
4. A Supabase Auth project. Provision user/organization claims through trusted
   Supabase app metadata. Set `app_metadata.graphtal_role` to `admin` or include
   `graphtal_admin` in `app_metadata.roles` for promotion/rollback permission.
   `app_metadata.organization_id` is the tenant boundary; if absent, the
   Supabase user ID is used as the tenant ID.

In Supabase Storage settings, create a private bucket and enable the S3
connection. Copy the S3 endpoint, region, Access Key ID, and Secret Access Key
from the S3 configuration page into the corresponding
`SUPABASE_STORAGE_*` and `SUPABASE_S3_*` variables. Use the direct storage
hostname and endpoint shown there. Supabase S3 access keys bypass Storage RLS
and can access all buckets, so keep them on the backend only and never expose
them to the frontend.

Apply the schema migration once, before deploying the registry-enabled API:

```sh
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f backend/migrations/001_model_registry.sql
```

Set the environment variables listed in `backend/.env.example` on both the
Render Web Service and Background Worker. The Render Web Service uses the
internal Postgres/Redis URLs. Keep Supabase S3 credentials, `DATABASE_URL`, and
any JWT signing secret in Render secret environment variables. Do not put
service-role keys or server credentials in `NEXT_PUBLIC_*` variables.

Suggested Render commands, with the service root set to the repository root:

```sh
# Web Service
cd backend && gunicorn main:app --workers 2 --worker-class gthread --threads 8 --bind 0.0.0.0:$PORT

# Background Worker
cd backend && rq worker model-training
```

Use one or more worker instances sized for the dataset/CPU limits. RQ retries a
failed job twice; candidate creation is idempotent per training job, module,
target, and algorithm. Configure Render health checks against `/`.

The Vercel project needs `NEXT_PUBLIC_API_URL`,
`NEXT_PUBLIC_SUPABASE_URL`, and `NEXT_PUBLIC_SUPABASE_ANON_KEY`. The API needs
`CORS_ALLOWED_ORIGINS` to include the exact Vercel origin and any local
development origin. The Supabase anon key is public by design; backend service
credentials are not.

## Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `DATABASE_URL` | API, worker, sync CLI | Render PostgreSQL connection string |
| `REDIS_URL` | API, worker | Render Key Value/Redis connection string |
| `SUPABASE_STORAGE_ENDPOINT` | API, worker, sync CLI | S3 endpoint copied from Supabase Storage settings |
| `SUPABASE_STORAGE_REGION` | API, worker, sync CLI | S3 region copied from Supabase Storage settings |
| `SUPABASE_STORAGE_BUCKET` | API, worker, sync CLI | Private Supabase Storage bucket name |
| `SUPABASE_S3_ACCESS_KEY_ID` | API, worker, sync CLI | Server-only Supabase S3 access key ID |
| `SUPABASE_S3_SECRET_ACCESS_KEY` | API, worker, sync CLI | Server-only Supabase S3 secret access key |
| `SUPABASE_URL` | API | Supabase project URL and JWT issuer. Falls back to `NEXT_PUBLIC_SUPABASE_URL`, then derives it from `SUPABASE_STORAGE_ENDPOINT` or a Supabase `DATABASE_URL` for shared deployment environments. |
| `SUPABASE_JWT_SECRET` | API (optional) | Use only for HS256-signed access tokens; otherwise API verifies Supabase JWKS |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Vercel | Supabase public anon key for browser login |
| `NEXT_PUBLIC_API_URL` | Vercel | Flask API base URL |
| `CORS_ALLOWED_ORIGINS` | API | Comma-separated exact allowed browser origins |
| `MODEL_REGISTRY_REFRESH_SECONDS` | API | Active-pointer poll interval; default `30` |
| `MODEL_MIN_TEST_R2` | API | Minimum candidate test R² for promotion; default `-1` |
| `MAX_TRAINING_ROWS` | API | Upload row cap; default `100000` |
| `MAX_EXCEL_UNCOMPRESSED_BYTES` | API | Expanded XLSX size cap; default `268435456` bytes |
| `MAX_ACTIVE_TRAINING_JOBS_PER_USER` | API | Concurrent queued/running job limit; default `3` |
| `TRAINING_TIMEOUT_SECONDS` | API | Queue job timeout; default `1800` |
| `MODEL_CACHE_DIR` | Local CLI/API | Optional versioned development cache directory |

Copy the example files for local development and fill them locally:

```sh
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Never commit those populated local files.

## Training, approval, and rollback

1. Sign into `/models` using a provisioned Supabase account.
2. Select Upstream or Formulation and upload a CSV/XLS/XLSX with all current
   schema input and output columns. Each required column must be numeric and
   complete. Files are limited to 100 MB and configured row limits.
3. The page submits the dataset, then queues a background job with an
   `Idempotency-Key`. The page polls persistent job status; completion means
   candidate models exist, not that production has changed.
4. An administrator reviews candidate test R², incumbent R², and the delta.
   Only a candidate that meets the incumbent comparison and configured minimum
   can be promoted.
5. Promotion/rollback updates Postgres in a transaction and writes an audit
   record. Other API processes adopt the pointer on their next poll. If an
   artifact cannot be verified or loaded, the process retains its previous
   working model and logs the refresh failure.
6. Administrators can use the page's “Refresh this API” control to force a
   refresh on the responding process. It does not synchronously reach other
   worker processes; their poll interval remains the cross-instance mechanism.

Failed jobs can be retried from the history list. A job's candidate writes are
idempotent, so a worker retry does not create duplicate versions.

## Local synchronization

Set `DATABASE_URL` and the `SUPABASE_STORAGE_*` and `SUPABASE_S3_*` values in
the local shell. The CLI intentionally uses database and object-storage access
directly; credentials must be kept private.

```sh
cd backend
python scripts/sync_models.py --module upstream --version latest
python scripts/sync_models.py --module formulation --version latest
```

`latest` selects current active versions (optionally narrowed with
`--target`/`--algorithm`). To pin a specific approved version, select its
numeric version with both target and algorithm, or its model UUID:

```sh
python scripts/sync_models.py --module upstream --target Titer --algorithm ridge --version 3
python scripts/sync_models.py --module formulation --version MODEL_UUID
```

The CLI verifies checksum, schema, algorithm, and feature count before
atomically updating the local `active.json` pointer. Artifacts are stored in a
versioned directory and the previous version is retained. On next API process
start, the predictor loads the pinned cache as its local fallback. Production
does not consult this developer cache.

## Existing model files and deployment rollback

Existing checked-in/local model files remain available as the compatibility
fallback and are not overwritten by registry training. They do not have
versioned dataset lineage or comparable holdout metrics in this repository, so
the application does not silently publish them as approved registry models.
To transition a target, upload its validated source dataset, train a candidate,
compare against the legacy model (the worker evaluates it on the candidate's
holdout set), and promote it after review.

For an application deployment rollback, revert the API/frontend release and
keep the database and bucket intact. To roll back only a model, use the
administrator rollback action for the archived version; the transaction
restores its active pointer and all API instances refresh from it. Do not
delete older artifact objects while any model version references them.

## Known limitations

- Downstream is not represented in the repository and is intentionally not
  registered or exposed by this implementation.
- Evaluation uses a deterministic random 80/20 holdout split. It is not a
  time-aware/experiment-aware split and should be upgraded if the dataset has
  temporal or batch leakage.
- Dataset uploads are automatically considered eligible after validation;
  there is no separate human dataset-approval state or dataset approval UI.
- Redis, Postgres, and Supabase are external managed services. End-to-end
  promotion, cross-instance refresh, and tenant authorization require
  configuring those services and cannot be verified from this checkout alone.
- The legacy `/retrain` and `/formulation-retrain` routes return HTTP 410 to
  prevent the former synchronous in-place model overwrite. Existing prediction
  route URLs and response shapes are retained.
