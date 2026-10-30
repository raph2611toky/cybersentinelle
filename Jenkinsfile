pipeline {
    agent any

    environment {
        BACKEND_DOCKER_IMAGE   = 'safidiko_backend'
        BACKEND_DOCKER_NAME    = 'safidiko-backend'
        DASHBOARD_DOCKER_IMAGE = 'safidiko_dashboard'
        DASHBOARD_DOCKER_NAME  = 'safidiko-dashboard'
        WORKER_DOCKER_NAME     = 'safidiko-worker'
        REDIS_DOCKER_IMAGE     = 'redis:7-alpine'
        REDIS_DOCKER_NAME      = 'safidiko-redis'

        APP_NETWORK = 'safidiko-network'
        BACKEND_PORT = '8466'
        DASHBOARD_PORT = '8467'

        SAFIDIKO_ENV  = '/var/lib/jenkins/secrets/safidiko'
        BACKEND_ENV   = '/var/lib/jenkins/secrets/safidiko/backend.env'
        DASHBOARD_ENV = '/var/lib/jenkins/secrets/safidiko/dashboard.env'

        MEDIA_DIR         = '/var/lib/jenkins/app/safidiko/media'
        PRIVATE_MEDIA_DIR = '/var/lib/jenkins/app/safidiko/private_media'
        STATIC_DIR        = '/var/lib/jenkins/app/safidiko/staticfiles'
        RELEASES_DIR      = '/var/lib/jenkins/app/safidiko/releases'
        REDIS_DIR         = '/var/lib/jenkins/app/safidiko/redis'
        MIGRATIONS_DIR    = '/var/lib/jenkins/app/safidiko/migrations'
        GOOGLE_SECRETS_DIR = '/var/lib/jenkins/secrets/safidiko/gcp'
    }

    triggers {
        GenericTrigger(
            genericVariables: [
                [key: 'git_branch', value: '$.ref'],
                [key: 'git_commit', value: '$.after']
            ],
            tokenCredentialId: 'safidiko-webhook-token',
            printContributedVariables: false,
            printPostContent: false,
            regexpFilterText: '$git_branch',
            regexpFilterExpression: 'refs/heads/' + BRANCH_NAME
        )
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 45, unit: 'MINUTES')
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Preflight') {
            steps {
                sh '''
                    set -eu
                    docker info >/dev/null

                    case "$BRANCH_NAME" in
                        backend)
                            test -f "$BACKEND_ENV" || { echo "Backend env manquant: $BACKEND_ENV"; exit 1; }
                            ;;
                        dashboard)
                            test -f "$DASHBOARD_ENV" || { echo "Dashboard env manquant: $DASHBOARD_ENV"; exit 1; }
                            ;;
                        rebuild)
                            test -f "$BACKEND_ENV" && test -f "$DASHBOARD_ENV" || {
                                echo 'Deux fichiers env requis pour rebuild'; exit 1;
                            }
                            ;;
                        *) echo "Branche sans déploiement: $BRANCH_NAME" ;;
                    esac

                    mkdir -p "$MEDIA_DIR" "$PRIVATE_MEDIA_DIR" "$STATIC_DIR" \
                        "$RELEASES_DIR" "$REDIS_DIR" "$MIGRATIONS_DIR" "$GOOGLE_SECRETS_DIR"
                    docker network inspect "$APP_NETWORK" >/dev/null 2>&1 \
                        || docker network create "$APP_NETWORK"
                '''
            }
        }

        stage('Build Backend') {
            when { anyOf { branch 'backend'; branch 'rebuild' } }
            steps {
                sh '''
                    set -eu
                    test -f backend/Dockerfile && test -f backend/requirements.txt
                    # Versioned Django migrations are immutable build inputs.
                    # Do not delete/recreate them: preserve data and migration history.
                    find backend/apps -type f -path '*/migrations/*.py' -print0 \
                        | tar --null --files-from=- -czf \
                          "$MIGRATIONS_DIR/migrations-${BUILD_NUMBER}.tar.gz"
                    docker build --pull \
                        -t "$BACKEND_DOCKER_IMAGE:$BUILD_NUMBER" \
                        -t "$BACKEND_DOCKER_IMAGE:latest" \
                        -f backend/Dockerfile backend

                    # New image uses UID 10001. Prepare persistent bind mounts.
                    docker run --rm --user 0 --entrypoint sh \
                        -v "$MEDIA_DIR:/mnt/media" \
                        -v "$PRIVATE_MEDIA_DIR:/mnt/private" \
                        -v "$STATIC_DIR:/mnt/static" \
                        -v "$RELEASES_DIR:/mnt/releases" \
                        -v "$GOOGLE_SECRETS_DIR:/mnt/secrets" \
                        "$BACKEND_DOCKER_IMAGE:$BUILD_NUMBER" \
                        -ec 'chown -R 10001:10001 /mnt/media /mnt/private /mnt/static /mnt/releases; chown 10001:10001 /mnt/secrets; chmod 700 /mnt/secrets; for file in /mnt/secrets/*.json; do [ -f "$file" ] || continue; chown 10001:10001 "$file"; chmod 600 "$file"; done'
                '''
            }
        }

        stage('Deploy Redis') {
            when { anyOf { branch 'backend'; branch 'rebuild' } }
            steps {
                sh '''
                    set -eu
                    docker image inspect "$REDIS_DOCKER_IMAGE" >/dev/null 2>&1 \
                        || docker pull "$REDIS_DOCKER_IMAGE"
                    if ! docker container inspect "$REDIS_DOCKER_NAME" >/dev/null 2>&1; then
                        docker run -d \
                            --name "$REDIS_DOCKER_NAME" \
                            --restart unless-stopped \
                            --network "$APP_NETWORK" \
                            -v "$REDIS_DIR:/data" \
                            "$REDIS_DOCKER_IMAGE" \
                            redis-server --appendonly yes
                    else
                        docker start "$REDIS_DOCKER_NAME" >/dev/null
                        docker network connect "$APP_NETWORK" "$REDIS_DOCKER_NAME" >/dev/null 2>&1 || true
                    fi
                    for i in 1 2 3 4 5 6 7 8 9 10; do
                        if docker exec "$REDIS_DOCKER_NAME" redis-cli ping 2>/dev/null | grep -q PONG; then
                            echo 'Redis prêt'; exit 0
                        fi
                        sleep 2
                    done
                    docker logs --tail 80 "$REDIS_DOCKER_NAME" || true
                    exit 1
                '''
            }
        }

        stage('Validate Backend & Migrations') {
            when { anyOf { branch 'backend'; branch 'rebuild' } }
            steps {
                sh '''
                    set -eu
                    docker run --rm \
                        --env-file "$BACKEND_ENV" \
                        -e CELERY_BROKER_URL="redis://$REDIS_DOCKER_NAME:6379/0" \
                        --network "$APP_NETWORK" \
                        --add-host=host.docker.internal:host-gateway \
                        -v "$GOOGLE_SECRETS_DIR:/run/secrets:ro" \
                        "$BACKEND_DOCKER_IMAGE:$BUILD_NUMBER" \
                        sh -ec 'python manage.py check && python manage.py makemigrations --check --dry-run --noinput && python manage.py migrate --plan'
                '''
            }
        }

        stage('Deploy Backend') {
            when { anyOf { branch 'backend'; branch 'rebuild' } }
            steps {
                sh '''
                    set -eu
                    # Apply schema changes while the old app is still running.
                    docker run --rm \
                        --env-file "$BACKEND_ENV" \
                        -e CELERY_BROKER_URL="redis://$REDIS_DOCKER_NAME:6379/0" \
                        --network "$APP_NETWORK" \
                        --add-host=host.docker.internal:host-gateway \
                        -v "$GOOGLE_SECRETS_DIR:/run/secrets:ro" \
                        -v "$MEDIA_DIR:/app/media" \
                        -v "$PRIVATE_MEDIA_DIR:/app/private_media" \
                        -v "$RELEASES_DIR:/app/content/releases" \
                        "$BACKEND_DOCKER_IMAGE:$BUILD_NUMBER" \
                        python manage.py migrate --noinput

                    docker run --rm \
                        --env-file "$BACKEND_ENV" \
                        --network "$APP_NETWORK" \
                        -v "$STATIC_DIR:/app/staticfiles" \
                        -v "$GOOGLE_SECRETS_DIR:/run/secrets:ro" \
                        "$BACKEND_DOCKER_IMAGE:$BUILD_NUMBER" \
                        python manage.py collectstatic --noinput

                    docker stop "$BACKEND_DOCKER_NAME" >/dev/null 2>&1 || true
                    docker rm "$BACKEND_DOCKER_NAME" >/dev/null 2>&1 || true
                    docker run -d \
                        --name "$BACKEND_DOCKER_NAME" \
                        --restart unless-stopped \
                        --env-file "$BACKEND_ENV" \
                        -e CELERY_BROKER_URL="redis://$REDIS_DOCKER_NAME:6379/0" \
                        --network "$APP_NETWORK" \
                        --add-host=host.docker.internal:host-gateway \
                        -v "$GOOGLE_SECRETS_DIR:/run/secrets:ro" \
                        -v "$MEDIA_DIR:/app/media" \
                        -v "$PRIVATE_MEDIA_DIR:/app/private_media" \
                        -v "$RELEASES_DIR:/app/content/releases" \
                        -v "$STATIC_DIR:/app/staticfiles" \
                        -p "127.0.0.1:$BACKEND_PORT:8000" \
                        "$BACKEND_DOCKER_IMAGE:$BUILD_NUMBER"

                    for i in 1 2 3 4 5 6 7 8 9 10; do
                        # Production Django redirects plain HTTP; this probe
                        # simulates the trusted TLS edge without storing secrets.
                        if curl -fsS \
                            -H 'Host: localhost' -H 'X-Forwarded-Proto: https' \
                            "http://127.0.0.1:$BACKEND_PORT/api/health/" \
                            | grep -q '"status"'; then
                            echo 'Backend prêt'; exit 0
                        fi
                        sleep 2
                    done
                    docker logs --tail 120 "$BACKEND_DOCKER_NAME" || true
                    exit 1
                '''
            }
        }

        stage('Deploy Celery Worker') {
            when { anyOf { branch 'backend'; branch 'rebuild' } }
            steps {
                sh '''
                    set -eu
                    docker stop "$WORKER_DOCKER_NAME" >/dev/null 2>&1 || true
                    docker rm "$WORKER_DOCKER_NAME" >/dev/null 2>&1 || true
                    docker run -d \
                        --name "$WORKER_DOCKER_NAME" \
                        --restart unless-stopped \
                        --env-file "$BACKEND_ENV" \
                        -e CELERY_BROKER_URL="redis://$REDIS_DOCKER_NAME:6379/0" \
                        --network "$APP_NETWORK" \
                        --add-host=host.docker.internal:host-gateway \
                        -v "$GOOGLE_SECRETS_DIR:/run/secrets:ro" \
                        -v "$MEDIA_DIR:/app/media" \
                        -v "$PRIVATE_MEDIA_DIR:/app/private_media" \
                        -v "$RELEASES_DIR:/app/content/releases" \
                        "$BACKEND_DOCKER_IMAGE:$BUILD_NUMBER" \
                        celery -A config worker --loglevel=info -Q translation,celery --concurrency=2
                    sleep 3
                    test "$(docker inspect -f '{{.State.Running}}' "$WORKER_DOCKER_NAME")" = true
                '''
            }
        }

        stage('Build Dashboard') {
            when { anyOf { branch 'dashboard'; branch 'rebuild' } }
            steps {
                sh '''
                    set -eu
                    test -f dashboard/Dockerfile && test -f dashboard/nginx.conf
                    # The dashboard env file may only hold PUBLIC VITE_* values.
                    VITE_BASE="$(sed -n 's/^VITE_API_BASE_URL=//p' "$DASHBOARD_ENV" | tail -n 1 | tr -d '\r')"
                    test "$VITE_BASE" = '/api' || {
                        echo 'Dashboard doit utiliser VITE_API_BASE_URL=/api (même origine)'; exit 1;
                    }
                    # Vite config is baked at build time, so there is no env-file
                    # passed to Nginx at runtime and no secret copied into the image.
                    docker build --pull \
                        --build-arg VITE_API_BASE_URL="$VITE_BASE" \
                        -t "$DASHBOARD_DOCKER_IMAGE:$BUILD_NUMBER" \
                        -t "$DASHBOARD_DOCKER_IMAGE:latest" \
                        -f dashboard/Dockerfile dashboard
                '''
            }
        }

        stage('Deploy Dashboard') {
            when { anyOf { branch 'dashboard'; branch 'rebuild' } }
            steps {
                sh '''
                    set -eu
                    docker stop "$DASHBOARD_DOCKER_NAME" >/dev/null 2>&1 || true
                    docker rm "$DASHBOARD_DOCKER_NAME" >/dev/null 2>&1 || true
                    docker run -d \
                        --name "$DASHBOARD_DOCKER_NAME" \
                        --restart unless-stopped \
                        --network "$APP_NETWORK" \
                        -v "$MEDIA_DIR:/srv/safidiko/media:ro" \
                        -v "$STATIC_DIR:/srv/safidiko/static:ro" \
                        -p "127.0.0.1:$DASHBOARD_PORT:80" \
                        "$DASHBOARD_DOCKER_IMAGE:$BUILD_NUMBER"
                    for i in 1 2 3 4 5 6 7 8 9 10; do
                        if curl -fsS "http://127.0.0.1:$DASHBOARD_PORT/dashboard" > /dev/null; then
                            echo 'Dashboard prêt'; exit 0
                        fi
                        sleep 2
                    done
                    docker logs --tail 120 "$DASHBOARD_DOCKER_NAME" || true
                    exit 1
                '''
            }
        }
    }

    post {
        always {
            // No secret files are copied into WORKSPACE by this pipeline.
            sh 'rm -f dashboard/.env.production backend/.env.production || true'
        }
        success { echo "✅ [${env.BRANCH_NAME}] Déploiement SAFIDIKO terminé." }
        failure { echo "❌ [${env.BRANCH_NAME}] Déploiement SAFIDIKO échoué." }
    }
}
