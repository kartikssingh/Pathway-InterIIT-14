#!/bin/bash
# =============================================================================
# Load Test Database Setup Script
# =============================================================================

set -e  # Exit on error

echo "=========================================="
echo "Load Test Database Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep DATABASE_URL | xargs)
fi

# If DATABASE_URL is not set, try to construct it
if [ -z "$DATABASE_URL" ]; then
    echo -e "${YELLOW}⚠️  DATABASE_URL not set, using default: postgresql://localhost/compliance_db${NC}"
    DATABASE_URL="postgresql://localhost/compliance_db"
fi

echo "🔌 Database URL: ${DATABASE_URL}"
echo ""

# Check if PostgreSQL is running
echo "📊 Checking PostgreSQL connection..."
if ! psql "$DATABASE_URL" -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot connect to PostgreSQL${NC}"
    echo ""
    echo "Trying alternative connection method..."
    
    # Extract database name from URL
    DB_NAME=$(echo "$DATABASE_URL" | sed -n 's|.*/\([^/?]*\).*|\1|p')
    
    if [ -z "$DB_NAME" ]; then
        DB_NAME="compliance_db"
    fi
    
    echo "Attempting to connect to database: $DB_NAME"
    
    if ! psql -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        echo -e "${RED}❌ Cannot connect to PostgreSQL${NC}"
        echo ""
        echo "Please check:"
        echo "  1. PostgreSQL is running: pg_isready"
        echo "  2. Database exists: psql -l | grep $DB_NAME"
        echo "  3. You have access: psql -d $DB_NAME"
        echo ""
        echo "To fix:"
        echo "  - Update DATABASE_URL in .env file"
        echo "  - Format: postgresql://username@localhost/database_name"
        echo "  - Or create database: createdb $DB_NAME"
        exit 1
    fi
    
    # Use the simple connection method if URL doesn't work
    PSQL_CMD="psql -d $DB_NAME"
else
    PSQL_CMD="psql $DATABASE_URL"
fi

echo -e "${GREEN}✅ PostgreSQL connection successful${NC}"
echo ""

# Show current data counts
echo "📈 Current database state:"
$PSQL_CMD -c "
    SELECT 'Users' as table_name, COUNT(*) as count FROM users
    UNION ALL
    SELECT 'Transactions', COUNT(*) FROM transactions
    UNION ALL
    SELECT 'Alerts', COUNT(*) FROM compliance_alerts
    UNION ALL
    SELECT 'Unclassified Alerts', COUNT(*) FROM compliance_alerts WHERE is_true_positive IS NULL;
" -t
echo ""

# Confirm before proceeding
echo -e "${YELLOW}⚠️  This will add:${NC}"
echo "  - 100 users (APP-2024-00001 to APP-2024-00100)"
echo "  - 500 transactions"
echo "  - 100 compliance alerts (40% unclassified)"
echo "  - 20 investigation cases"
echo ""
echo -e "${YELLOW}Note: Existing data will NOT be deleted${NC}"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled by user"
    exit 0
fi

# Run the population script
echo ""
echo "🔄 Populating database with test data..."
echo ""

if $PSQL_CMD -f populate_load_test_data.sql; then
    echo ""
    echo -e "${GREEN}✅ Database populated successfully!${NC}"
    echo ""
    
    # Show final counts
    echo "📊 Final database state:"
    $PSQL_CMD -c "
        SELECT 
            'Users' as resource,
            COUNT(*) as total,
            'ID range: 1-' || MAX(id) as info
        FROM users
        UNION ALL
        SELECT 
            'Transactions',
            COUNT(*),
            'ID range: 1-' || MAX(id)
        FROM transactions
        UNION ALL
        SELECT 
            'Compliance Alerts (Total)',
            COUNT(*),
            COUNT(*) FILTER (WHERE is_true_positive IS NULL)::TEXT || ' unclassified'
        FROM compliance_alerts
        UNION ALL
        SELECT 
            'Investigation Cases',
            COUNT(*),
            ''
        FROM investigation_cases;
    "
    
    echo ""
    echo -e "${GREEN}=========================================="
    echo "✅ Setup Complete!"
    echo "==========================================${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start backend: uvicorn app.main:app --reload"
    echo "  2. Run Locust: cd tests/load && locust -f locustfile.py"
    echo "  3. Open browser: http://localhost:8089"
    echo ""
    echo "For detailed instructions, see: tests/load/LOAD_TEST_SETUP.md"
    
else
    echo ""
    echo -e "${RED}❌ Error populating database${NC}"
    echo "Check the error messages above for details"
    exit 1
fi
