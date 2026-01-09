"""
Fraud Detection Service - Phase 6 of Forensic Audit Framework

Implements Big 5 accounting firm fraud detection methodology:
- Benford's Law Analysis (Rule A-6.1)
- Round Number Analysis (Rule A-6.2)
- Duplicate Payment Detection (Rule A-6.3)
- Variance Analysis Period-over-Period (Rule A-6.4)
- Cash Ratio Analysis (Rule A-6.8)
"""

from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
import numpy as np
from scipy.stats import chisquare
import math
from collections import Counter


class FraudDetectionService:
    """
    Detects potential fraud indicators using statistical analysis.

    Methods implement forensic accounting best practices from Big 5 firms.
    """

    # Benford's Law expected first digit distribution (%)
    BENFORDS_EXPECTED = {
        1: 30.1,
        2: 17.6,
        3: 12.5,
        4: 9.7,
        5: 7.9,
        6: 6.7,
        7: 5.8,
        8: 5.1,
        9: 4.6
    }

    # Chi-square critical values
    CHI_SQUARE_CRITICAL_005 = 15.51  # α=0.05, df=8
    CHI_SQUARE_MANIPULATION = 20.09  # Strong evidence of manipulation

    # Round number thresholds
    ROUND_NUMBER_NORMAL = 5.0  # <5% is normal
    ROUND_NUMBER_WARNING = 10.0  # 5-10% monitor
    ROUND_NUMBER_RED_FLAG = 15.0  # >10% suggests fabrication

    # Cash conversion ratio thresholds
    CASH_CONVERSION_EXCELLENT = 0.95  # >95%
    CASH_CONVERSION_GOOD = 0.90  # 90-95%
    CASH_CONVERSION_WARNING = 0.80  # 80-90%
    CASH_CONVERSION_CRITICAL = 0.70  # <70% requires investigation

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_all_fraud_tests(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Run complete fraud detection test suite.

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Complete fraud detection results
        """

        # Run all tests in parallel
        benfords_result = await self.benfords_law_analysis(property_id, period_id)
        round_number_result = await self.round_number_analysis(property_id, period_id)
        duplicate_result = await self.duplicate_payment_detection(property_id, period_id)
        cash_ratio_result = await self.cash_ratio_analysis(property_id, period_id)

        # Determine overall fraud risk level
        red_flags = 0
        if benfords_result['status'] == 'RED':
            red_flags += 2
        elif benfords_result['status'] == 'YELLOW':
            red_flags += 1

        if round_number_result['status'] == 'RED':
            red_flags += 2
        elif round_number_result['status'] == 'YELLOW':
            red_flags += 1

        if duplicate_result['duplicate_count'] > 0:
            red_flags += 3  # Duplicates are very serious

        if cash_ratio_result['status'] == 'RED':
            red_flags += 2
        elif cash_ratio_result['status'] == 'YELLOW':
            red_flags += 1

        # Overall risk level
        if red_flags >= 5:
            overall_risk = 'RED'
        elif red_flags >= 2:
            overall_risk = 'YELLOW'
        else:
            overall_risk = 'GREEN'

        return {
            'property_id': str(property_id),
            'period_id': str(period_id),
            'overall_fraud_risk_level': overall_risk,
            'red_flags_found': red_flags,
            'benfords_law': benfords_result,
            'round_numbers': round_number_result,
            'duplicate_payments': duplicate_result,
            'cash_conversion': cash_ratio_result,
            'tested_at': datetime.now().isoformat()
        }

    async def benfords_law_analysis(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-6.1: Benford's Law Analysis

        Analyzes first digit distribution of financial transactions.
        Natural data follows Benford's Law (digit 1 appears ~30.1% of time).
        Fabricated data shows abnormal distribution.

        Chi-square test:
        - χ² < 15.51: Normal (α=0.05)
        - χ² 15.51-20.09: Warning
        - χ² > 20.09: Likely manipulation

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Benford's Law test results with chi-square statistic
        """

        # Get all expense transactions for the period
        query = text("""
            SELECT period_amount
            FROM income_statement_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND period_amount > 0
            AND account_code LIKE '5%'  -- Expense accounts
        """)

        result = await self.db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        transactions = result.fetchall()

        if len(transactions) < 30:
            return {
                'status': 'INSUFFICIENT_DATA',
                'chi_square': None,
                'message': f'Need at least 30 transactions, found {len(transactions)}'
            }

        # Extract first digits
        first_digits = []
        for row in transactions:
            amount = float(row[0])
            if amount > 0:
                # Get first non-zero digit
                amount_str = f"{amount:.2f}".replace('.', '').lstrip('0')
                if amount_str:
                    first_digit = int(amount_str[0])
                    if 1 <= first_digit <= 9:
                        first_digits.append(first_digit)

        if len(first_digits) < 30:
            return {
                'status': 'INSUFFICIENT_DATA',
                'chi_square': None,
                'message': 'Insufficient valid first digits'
            }

        # Count first digit frequencies
        digit_counts = Counter(first_digits)
        total_count = len(first_digits)

        # Calculate observed and expected frequencies
        observed = []
        expected = []
        digit_distribution = {}

        for digit in range(1, 10):
            obs_count = digit_counts.get(digit, 0)
            obs_pct = (obs_count / total_count) * 100
            exp_pct = self.BENFORDS_EXPECTED[digit]
            exp_count = (exp_pct / 100) * total_count

            observed.append(obs_count)
            expected.append(exp_count)

            digit_distribution[digit] = {
                'observed_count': obs_count,
                'observed_pct': round(obs_pct, 2),
                'expected_pct': exp_pct,
                'variance': round(obs_pct - exp_pct, 2)
            }

        # Chi-square test
        chi_square_stat, p_value = chisquare(observed, expected)
        chi_square_stat = float(chi_square_stat)

        # Determine status
        if chi_square_stat > self.CHI_SQUARE_MANIPULATION:
            status = 'RED'
            interpretation = 'Strong evidence of data manipulation'
        elif chi_square_stat > self.CHI_SQUARE_CRITICAL_005:
            status = 'YELLOW'
            interpretation = 'Deviation from Benford\'s Law - investigate further'
        else:
            status = 'GREEN'
            interpretation = 'Distribution follows Benford\'s Law'

        return {
            'status': status,
            'chi_square': round(chi_square_stat, 2),
            'p_value': round(p_value, 4),
            'critical_value_005': self.CHI_SQUARE_CRITICAL_005,
            'manipulation_threshold': self.CHI_SQUARE_MANIPULATION,
            'sample_size': total_count,
            'digit_distribution': digit_distribution,
            'interpretation': interpretation
        }

    async def round_number_analysis(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-6.2: Round Number Analysis

        Detects fabrication by analyzing prevalence of round numbers.
        Natural transactions rarely end in 00, 000, etc.
        High percentage of round numbers suggests estimation or fabrication.

        Thresholds:
        - <5%: Normal
        - 5-10%: Monitor
        - >10%: Red flag (fabrication likely)

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Round number analysis results
        """

        # Get all transactions
        query = text("""
            SELECT period_amount
            FROM income_statement_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND period_amount > 0
        """)

        result = await self.db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        transactions = result.fetchall()

        if len(transactions) < 10:
            return {
                'status': 'INSUFFICIENT_DATA',
                'round_number_pct': None,
                'message': f'Need at least 10 transactions, found {len(transactions)}'
            }

        # Count round numbers
        round_count = 0
        round_100_count = 0
        round_1000_count = 0

        for row in transactions:
            amount = float(row[0])

            # Check if divisible by 1000
            if amount >= 1000 and amount % 1000 == 0:
                round_1000_count += 1
                round_count += 1
            # Check if divisible by 100
            elif amount >= 100 and amount % 100 == 0:
                round_100_count += 1
                round_count += 1
            # Check if divisible by 10 (ends in 0)
            elif amount % 10 == 0:
                round_count += 1

        total_count = len(transactions)
        round_pct = (round_count / total_count) * 100

        # Determine status
        if round_pct > self.ROUND_NUMBER_RED_FLAG:
            status = 'RED'
            interpretation = f'{round_pct:.1f}% round numbers suggests fabrication'
        elif round_pct > self.ROUND_NUMBER_WARNING:
            status = 'YELLOW'
            interpretation = f'{round_pct:.1f}% round numbers - monitor for patterns'
        else:
            status = 'GREEN'
            interpretation = f'{round_pct:.1f}% round numbers is normal'

        return {
            'status': status,
            'round_number_pct': round(round_pct, 2),
            'round_number_count': round_count,
            'round_100_count': round_100_count,
            'round_1000_count': round_1000_count,
            'total_transactions': total_count,
            'interpretation': interpretation
        }

    async def duplicate_payment_detection(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-6.3: Duplicate Payment Detection

        Identifies potential fictitious payments by finding duplicates.
        Exact amount + same vendor + same date = high fraud risk.

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Duplicate payment analysis
        """

        # Find duplicate payments (same amount, vendor, date)
        query = text("""
            SELECT
                account_code,
                account_name,
                period_amount,
                COUNT(*) as duplicate_count
            FROM income_statement_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND period_amount > 100  -- Only flag amounts > $100
            GROUP BY account_code, account_name, period_amount
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC, period_amount DESC
        """)

        result = await self.db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        duplicates = result.fetchall()

        duplicate_details = []
        total_duplicate_amount = 0

        for row in duplicates:
            account_code = row[0]
            description = row[1]
            amount = float(row[2])
            count = row[3]

            duplicate_details.append({
                'account_code': account_code,
                'description': description,
                'amount': amount,
                'occurrence_count': count,
                'total_duplicate_amount': amount * (count - 1)  # Exclude first occurrence
            })

            total_duplicate_amount += amount * (count - 1)

        duplicate_count = len(duplicates)

        return {
            'duplicate_count': duplicate_count,
            'total_duplicate_amount': round(total_duplicate_amount, 2),
            'duplicate_details': duplicate_details,
            'status': 'RED' if duplicate_count > 0 else 'GREEN',
            'interpretation': f'Found {duplicate_count} potential duplicate payments' if duplicate_count > 0 else 'No duplicate payments detected'
        }

    async def cash_ratio_analysis(
        self,
        property_id: UUID,
        period_id: UUID
    ) -> Dict[str, Any]:
        """
        Rule A-6.8: Cash Ratio Analysis

        Compares cash flow to net income (cash conversion ratio).
        Large divergence suggests accrual manipulation or revenue recognition issues.

        Expected ratio: ~0.90-1.10 (cash flow ≈ net income)
        Red flags:
        - <0.70: Profits not converting to cash (revenue recognition issue?)
        - >1.30: Cash exceeds income (one-time items?)

        Args:
            property_id: Property UUID
            period_id: Financial period UUID

        Returns:
            Cash conversion ratio analysis
        """

        # Get net income from income statement
        is_query = text("""
            SELECT SUM(period_amount) as net_income
            FROM income_statement_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND account_code = '99999'  -- Net income line
        """)

        is_result = await self.db.execute(
            is_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        is_row = is_result.fetchone()
        net_income = float(is_row[0]) if is_row and is_row[0] else 0

        # Get cash flow from operations from cash flow statement
        cf_query = text("""
            SELECT SUM(period_amount) as cash_from_operations
            FROM cash_flow_data
            WHERE property_id = :property_id
            AND period_id = :period_id
            AND cash_flow_category ILIKE 'operating'
        """)

        cf_result = await self.db.execute(
            cf_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        cf_row = cf_result.fetchone()
        cash_from_operations = float(cf_row[0]) if cf_row and cf_row[0] else 0

        # Calculate cash conversion ratio
        if net_income != 0:
            cash_conversion_ratio = cash_from_operations / net_income
        else:
            cash_conversion_ratio = 0

        # Determine status
        if cash_conversion_ratio < self.CASH_CONVERSION_CRITICAL:
            status = 'RED'
            interpretation = f'Cash conversion {cash_conversion_ratio:.2f}x is critically low - investigate revenue recognition'
        elif cash_conversion_ratio < self.CASH_CONVERSION_WARNING:
            status = 'YELLOW'
            interpretation = f'Cash conversion {cash_conversion_ratio:.2f}x is below normal - monitor A/R and accruals'
        elif cash_conversion_ratio > 1.30:
            status = 'YELLOW'
            interpretation = f'Cash conversion {cash_conversion_ratio:.2f}x is unusually high - verify one-time items'
        else:
            status = 'GREEN'
            interpretation = f'Cash conversion {cash_conversion_ratio:.2f}x is healthy'

        return {
            'status': status,
            'cash_conversion_ratio': round(cash_conversion_ratio, 2),
            'net_income': round(net_income, 2),
            'cash_from_operations': round(cash_from_operations, 2),
            'variance': round(cash_from_operations - net_income, 2),
            'interpretation': interpretation
        }

    async def save_fraud_detection_results(
        self,
        property_id: UUID,
        period_id: UUID,
        results: Dict[str, Any]
    ) -> None:
        """
        Save fraud detection results to database.

        Args:
            property_id: Property UUID
            period_id: Financial period UUID
            results: Complete fraud detection results
        """

        benfords = results['benfords_law']
        round_nums = results['round_numbers']
        duplicates = results['duplicate_payments']
        cash_ratio = results['cash_conversion']

        insert_query = text("""
            INSERT INTO fraud_detection_results (
                property_id,
                period_id,
                benfords_law_chi_square,
                benfords_law_status,
                round_number_pct,
                round_number_status,
                duplicate_payment_count,
                duplicate_payment_details,
                cash_conversion_ratio,
                cash_ratio_status,
                overall_fraud_risk_level,
                red_flags_found,
                test_details,
                created_at
            ) VALUES (
                :property_id,
                :period_id,
                :benfords_chi_square,
                :benfords_status,
                :round_pct,
                :round_status,
                :dup_count,
                :dup_details,
                :cash_ratio,
                :cash_status,
                :overall_risk,
                :red_flags,
                :test_details,
                NOW()
            )
            ON CONFLICT (property_id, period_id)
            DO UPDATE SET
                benfords_law_chi_square = EXCLUDED.benfords_law_chi_square,
                benfords_law_status = EXCLUDED.benfords_law_status,
                round_number_pct = EXCLUDED.round_number_pct,
                round_number_status = EXCLUDED.round_number_status,
                duplicate_payment_count = EXCLUDED.duplicate_payment_count,
                duplicate_payment_details = EXCLUDED.duplicate_payment_details,
                cash_conversion_ratio = EXCLUDED.cash_conversion_ratio,
                cash_ratio_status = EXCLUDED.cash_ratio_status,
                overall_fraud_risk_level = EXCLUDED.overall_fraud_risk_level,
                red_flags_found = EXCLUDED.red_flags_found,
                test_details = EXCLUDED.test_details,
                updated_at = NOW()
        """)

        import json

        await self.db.execute(
            insert_query,
            {
                "property_id": str(property_id),
                "period_id": str(period_id),
                "benfords_chi_square": benfords.get('chi_square'),
                "benfords_status": benfords['status'],
                "round_pct": round_nums.get('round_number_pct'),
                "round_status": round_nums['status'],
                "dup_count": duplicates['duplicate_count'],
                "dup_details": json.dumps(duplicates['duplicate_details']),
                "cash_ratio": cash_ratio.get('cash_conversion_ratio'),
                "cash_status": cash_ratio['status'],
                "overall_risk": results['overall_fraud_risk_level'],
                "red_flags": results['red_flags_found'],
                "test_details": json.dumps(results)
            }
        )

        await self.db.commit()
