#!/usr/bin/env python3
"""
Test Yahoo Finance integration with the bot.
"""

print('Testing bot imports...')

try:
    from simple_bot import detect_stock_query, get_stock_data_response
    from yahoo_finance import yahoo_finance
    print('✅ All imports successful!')
    
    # Test detection
    test_queries = [
        'What is Apple stock price?',
        'Show me MSFT quote',
        'market summary',
        'Tell me about portfolio theory'
    ]
    
    for query in test_queries:
        print(f'\nTesting: "{query}"')
        stock_query = detect_stock_query(query)
        print(f'Detection: {stock_query}')
        
        if stock_query['type'] != 'none':
            response = get_stock_data_response(stock_query)
            print(f'Response: {response[:150]}...')
        else:
            print('No stock query detected - would use RAG system')
    
    print('\n✅ Yahoo Finance integration fully operational!')
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()