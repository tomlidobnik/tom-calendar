#!/bin/bash
set -euo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
trap 'echo "❌ Script failed at line $LINENO: $BASH_COMMAND" >&2' ERR
set -a; source "$(dirname "$0")/.env"; set +a
mkdir -p schedule

TOKEN=$(curl -s 'https://wise-tt.com/WTTWebRestAPI/ws/rest/login' \
  -H "Authorization: Basic $WISE_BASIC_AUTH" | jq -r '.token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Failed to get token!"
    exit 1
fi

# UMETNA INTELIGENCA
curl -s 'https://www.wise-tt.com/WTTWebRestAPI/ws/rest/scheduleByCourse?schoolCode=wtt_um_feri&dateFrom=2026-01-01&dateTo=2026-07-01&language=slo&courseId=811' \
  -H "Authorization: Bearer $TOKEN" | jq '.' > schedule/811.json

#  ALGORITMI IN TEHNIKE ZA UCINKOVITO RESEVANJE PROBLEMOV
curl -s 'https://www.wise-tt.com/WTTWebRestAPI/ws/rest/scheduleByCourse?schoolCode=wtt_um_feri&dateFrom=2026-01-01&dateTo=2026-07-01&language=slo&courseId=1445' \
  -H "Authorization: Bearer $TOKEN" | jq '.' > schedule/1445.json

# SOCIOLOSKI IN POKLICNI VIDIKI
curl -s 'https://www.wise-tt.com/WTTWebRestAPI/ws/rest/scheduleByCourse?schoolCode=wtt_um_feri&dateFrom=2026-01-01&dateTo=2026-07-01&language=slo&courseId=1025' \
  -H "Authorization: Bearer $TOKEN" | jq '.' > schedule/1025.json

# INTERAKCIJA CLOVEK-RACUNALNIK
curl -s 'https://www.wise-tt.com/WTTWebRestAPI/ws/rest/scheduleByCourse?schoolCode=wtt_um_feri&dateFrom=2026-01-01&dateTo=2026-07-01&language=slo&courseId=1486' \
  -H "Authorization: Bearer $TOKEN" | jq '.' > schedule/1486.json

#VESCINE KOMUNICIRANJA V INZENIRSKEM POKLICU
curl -s 'https://www.wise-tt.com/WTTWebRestAPI/ws/rest/scheduleByCourse?schoolCode=wtt_um_feri&dateFrom=2026-01-01&dateTo=2026-07-01&language=slo&courseId=1444' \
  -H "Authorization: Bearer $TOKEN" | jq '.' > schedule/1444.json
