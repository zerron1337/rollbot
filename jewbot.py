import json
import asyncio
import locale

str_delimiter = r'[ ,.;]'
currency_symbol = '₪'
prefix = ''
accounts = {}
bets = {}
saving_flag = False
recalc_flag = False
save_data_flag = False
recalc_period = 1
save_period = 60

default_profit = 0.10
tier_profit = 0.02
asset_types = {
    "1": {'name': 'Negro', 'price': 50},
    "2": {'name': 'Wageslave', 'price': 200},
    "3": {'name': 'JEWelry Store', 'price': 2000},
    "4": {'name': 'Mass Media Company', 'price': 10000},
    "5": {'name': '3rd World Country', 'price': 100000},
    "6": {'name': '1st World Country', 'price': 1000000},
    "7": {'name': 'Moon', 'price': 1000000000},
    "8": {'name': 'Solar System', 'price': 100000000000}
}

bet_win_cut = 0.1


def init():
    global accounts, bets
    accounts = load_accounts()
    bets = load_bets()
    asyncio.ensure_future(recalculate_balances())
    asyncio.ensure_future(save_data())


async def save_data():
    global save_data_flag, saving_flag
    if save_data_flag:
        return
    save_data_flag = True
    await asyncio.sleep(save_period)
    saving_flag = True
    f = open('jewbot_accounts.json', 'w')
    json.dump(accounts, f, indent=4)
    f.close()
    f = open('jewbot_bets.json', 'w')
    json.dump(bets, f, indent=4)
    f.close()
    saving_flag = False
    save_data_flag = False

    asyncio.ensure_future(save_data())


async def recalculate_balances():
    global recalc_flag
    if recalc_flag:
        return

    recalc_flag = True
    await asyncio.sleep(recalc_period)
    if saving_flag:
        asyncio.ensure_future(recalculate_balances())
        return
    for user_id in accounts:
        for asset_id in accounts[user_id]['assets']:
            accounts[user_id]['balance'] += (
                (
                    asset_types[asset_id]['price'] *
                    (default_profit + tier_profit * (int(asset_id) - 1))
                ) *
                (
                    (recalc_period / 3600) *
                    accounts[user_id]['assets'][asset_id]
                )
            )
    recalc_flag = False

    asyncio.ensure_future(recalculate_balances())


def load_accounts():
    result = {}
    try:
        f = open('jewbot_accounts.json', 'r')
        result = json.load(f)
        f.close()
    except FileNotFoundError:
        f = open('jewbot_accounts.json', 'w')
        f.close()
    except:
        print('[ERROR] Failed to load accounts file!')
    return result


def load_bets():
    result = {}
    try:
        f = open('jewbot_bets.json', 'r')
        result = json.load(f)
        f.close()
    except FileNotFoundError:
        f = open('jewbot_bets.json', 'w')
        f.close()
    except:
        print('[ERROR] Failed to load bets file!')
    return result


def get_account(user_id):
    if user_id not in accounts:
        accounts[user_id] = {'balance': 75, 'assets': {}}
    return accounts[user_id]


def update_balance(user_id, amount):
    get_account(user_id)
    accounts[user_id]['balance'] += amount


def get_bet(user_id):
    if user_id in bets:
        return bets[user_id]
    else:
        return None


def bet(user_id, amount):
    get_account(user_id)
    if accounts[user_id]['balance'] < amount:
        return False
    current_bet = get_bet(user_id)
    if current_bet is None:
        bets[user_id] = amount
    else:
        bets[user_id] = current_bet + amount
    accounts[user_id]['balance'] -= amount
    return bets[user_id]


def clear_bet(user_id):
    if user_id in bets:
        del bets[user_id]


def get_payoff(lower, upper, roll):
    n = repeating_digits_count(roll)
    if n < 2:
        if upper - lower + 1 >= 11:
            return 0
    lower0 = lower
    upper0 = upper
    if n > 2:
        mult = 10 ** (n - 2)
        lower = int(lower / mult)
        upper = int(upper / mult)
        if lower < 1:
            lower = 1
        if repeating_digits_count(lower) >= 2:
            x = lower % 10
            y = x
            for i in range(1, n - 2):
                y = y * 10 + x
            if (lower * mult + y) < lower0:
                lower += 1
        if repeating_digits_count(upper) >= 2:
            x = upper % 10
            y = x
            for i in range(1, n - 2):
                y = y * 10 + x
            if (upper * mult + y) > upper0:
                upper -= 1
        n = 2
    total = upper - lower + 1
    if total < 2:
        return False
    winning = 0
    div = 10 ** n
    lower2 = int(lower / div) * div + div
    upper2 = int(upper / div) * div
    if lower2 > upper:
        for i in range(lower, upper + 1):
            c = repeating_digits_count(i)
            if c >= 2 and c >= n:
                winning += 1
    else:
        winning = int((upper2 - lower2) / div) * 10
        for i in range(lower, lower2 + 1):
            c = repeating_digits_count(i)
            if c >= 2 and c >= n:
                winning += 1
        for i in range(upper2 + 1, upper + 1):
            c = repeating_digits_count(i)
            if c >= 2 and c >= n:
                winning += 1
    if winning < 1:
        return False
    if n < 2:
        return 0
    total = upper0 - lower0 + 1 - winning
    return ((total / winning) + 1) * (1 - 0.1)


def repeating_digits_count(number):
    n = 1
    div = 1
    scale = 10 ** n
    while (number % scale) % div == 0:
        n += 1
        div = 1
        scale = 10 ** n
        for i in range(1, n):
            div = div * 10 + 1
    return n - 1


def find_asset(asset_name):
    asset_names = {}
    for asset_id in asset_types:
        asset_names[asset_id] = asset_types[asset_id]['name']
    results = word_search(asset_name, asset_names)
    return results[0] if len(results) > 0 else None


def word_search(needle, haystack):
    if type(haystack) is list:
        haystack = dict(enumerate(haystack))
    matches = {}
    import re
    words = list(filter(None, re.split(str_delimiter, str(needle))))
    for key in haystack:
        item_words = list(filter(None, re.split(str_delimiter, str(haystack[key]))))
        if key not in matches:
            matches[key] = {'words': 0, 'order': 0}
        last_match_position = 0
        if needle.lower() == haystack[key].lower():
            matches[key] = {'words': 1000, 'order': 1000}
            break
        for word in words:
            i = 1
            for item_word in item_words:
                if word.lower() in item_word.lower():
                    matches[key]['words'] += 1
                    if i > last_match_position:
                        matches[key]['order'] += 1
                    last_match_position = i
                    break
                i += 1
    sorted_matches = sorted(matches.items(), key=lambda x: x[1]['words'] + x[1]['order'], reverse=True)
    result = []
    best = sorted_matches[0][1]
    if best['words'] > 0:
        for match in sorted_matches:
            if match[1]['words'] >= best['words']:
                result.append(match[0])
    return result


def buy(user_id, asset_id, amount):
    get_account(user_id)
    if int(accounts[user_id]['balance']) < int(asset_types[asset_id]['price'] * amount):
        return False
    else:
        accounts[user_id]['balance'] -= asset_types[asset_id]['price'] * amount
        if asset_id not in accounts[user_id]['assets']:
            accounts[user_id]['assets'][asset_id] = amount
        else:
            accounts[user_id]['assets'][asset_id] += amount
        return True


def pay(from_id, to_id, amount):
    get_account(from_id)
    get_account(to_id)
    if accounts[from_id]['balance'] < amount:
        return False
    else:
        accounts[from_id]['balance'] -= amount
        accounts[to_id]['balance'] += amount
        return True


def get_assets_types_msg():
    msg = '%sAssets available for purchase:\n' % prefix
    for asset_id in sorted(asset_types.keys()):
        msg += '%s - %s%s' % (asset_types[asset_id]['name'], int_fmt(asset_types[asset_id]['price']), currency_symbol)
        profit = asset_types[asset_id]['price'] * (default_profit + tier_profit * (int(asset_id) - 1))
        msg += ' (%s%s per hour)\n' % (int_fmt(profit), currency_symbol)
    return msg


def get_assets_list_msg(user_id):
    account = get_account(user_id)
    if len(account['assets']) < 1:
        msg = '%sYou don\'t own any assets.' % prefix
    else:
        msg = '%sList of your assets:\n' % prefix
        assets = {}
        total_profit = 0
        for asset_id in sorted(account['assets'].keys()):
            assets[asset_id] = {
                'count': account['assets'][asset_id],
                'name': asset_types[asset_id]['name'],
                'profit': (
                    asset_types[asset_id]['price'] *
                    (default_profit + tier_profit * (int(asset_id) - 1)) *
                    account['assets'][asset_id]
               )
            }
            total_profit += assets[asset_id]['profit']
        for i in assets:
            msg += '%s %s, ' % (int_fmt(assets[i]['count']), assets[i]['name'])
        msg = msg[:-1]
        msg += '\nTotal hourly profit: %s%s' % (int_fmt(total_profit), currency_symbol)
    return msg


def int_fmt(num):
    return locale.format("%d", num, grouping=True)