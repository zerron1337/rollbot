import discord
import random
import time
import re
import json
import jewbot
import certifi
import io
import urllib3
import locale
import asyncio
import triviabot

from cleverwrap import CleverWrap
from PIL import Image

locale.setlocale(locale.LC_ALL, 'en_US.utf8')

test_token = ''
prod_token = ''
client = discord.Client()

active_questions = {}
answer_time = 15
default_win = 5

cooldowns = {}
ability_cds = {}
default_cd = 30
ignored = {}

conversations = {}

anon_msg_channel_id = '120824230806814722'
spam_channel_id = '212563711821479937'

clever_api_key = ''

dubs_power_str = {
    1: None,
    10: None,
    2: 'dubs',
    20: 'fake dubs',
    3: 'trips',
    30: 'fake trips',
    4: 'quads',
    40: 'fake quads',
    5: 'quints',
    50: 'fake quints',
    6: 'GET',
    60: 'fake GET'
}
default_roll = {}


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    jewbot.init()
    global default_roll
    try:
        f = open('default_rolls.json', 'r')
        default_roll = json.load(f)
        f.close()
    except:
        pass


@client.event
async def on_message(message):
    if message.author.id != client.user.id:
        reg_answer(message.channel.id, message.author.id, message.content)
    try:
        if message.content.startswith('<@%s>' % client.user.id) or (message.content.endswith('<@%s>' % client.user.id) and
                 not message.content.startswith('/')):
            await client.send_typing(message.channel)
            input_text = message.content.replace('<@%s>' % client.user.id, '').strip()
            if message.author not in conversations:
                conversations[message.author] = CleverWrap(clever_api_key)
            reply_text = conversations[message.author].say(input_text)
            time.sleep(0.15 * len(reply_text))
            await client.send_message(message.channel, '<@%s>, %s' % (message.author.id, reply_text))
        elif message.content.startswith('/default'):
            try:
                cd = get_cd('default', message.author)
                if cd:
                    if ignored[message.author] == 0:
                        await client.send_message(message.channel,
                                                  '```diff\n- Ability is not ready yet. (%d sec CD) -\n```' % cd)
                        ignored[message.author] = 1
                    return
            except KeyError:
                pass
            args = re.split(' |-', message.content[len('/default '):], 2)
            lower = 1
            upper = 100
            try:
                arg1 = int(args[0])
                if arg1 > 0:
                    try:
                        arg2 = int(args[1])
                        if arg2 > 0 and arg2 >= arg1:
                            lower = arg1
                            upper = arg2
                        else:
                            upper = arg1
                    except (ValueError, IndexError):
                        upper = arg1
            except (ValueError, IndexError):
                pass
            default_roll[message.author.id] = {
                'lower': lower,
                'upper': upper
            }
            set_cd('default', message.author)
            ignored[message.author] = 0
            f = open('default_rolls.json', 'w')
            json.dump(default_roll, f, indent=4)
            f.close()
            await client.send_message(message.channel,
                                      '```diff\n+ Default roll set to %d-%d +\n```' % (lower, upper))
        elif message.content.startswith('/roll'):
            try:
                cd = get_cd('roll', message.author)
                if cd:
                    if ignored[message.author] == 0:
                        await client.send_message(message.channel,
                                                  '```diff\n- Ability is not ready yet. (%d sec CD) -\n```' % cd)
                        ignored[message.author] = 1
                    return
            except KeyError:
                pass
            args = re.split(' |-', message.content[len('/roll '):], 2)
            if message.author.id in default_roll:
                lower = default_roll[message.author.id]['lower']
                upper = default_roll[message.author.id]['upper']
            else:
                lower = 1
                upper = 100
            try:
                arg1 = int(args[0])
                if arg1 > 0:
                    try:
                        arg2 = int(args[1])
                        if arg2 > 0 and arg2 >= arg1:
                            lower = arg1
                            upper = arg2
                        else:
                            upper = arg1
                    except (ValueError, IndexError):
                        upper = arg1
            except (ValueError, IndexError):
                pass
            random.seed()
            roll = random.randint(lower, upper)
            bet = jewbot.get_bet(message.author.id)
            payoff = 0
            if bet is not None:
                payoff = jewbot.get_payoff(lower, upper, roll)
                if payoff is not False:
                    jewbot.clear_bet(message.author.id)
            if message.channel.id != spam_channel_id:
                set_cd('roll', message.author)
            ignored[message.author] = 0
            roll_power = get_dubs_power(roll, lower, upper)
            if roll_power is not None:
                await client.send_message(message.channel, '```md\n[%s rolls %d (%d-%d).][%s]\n```' % (
                    message.author.display_name, roll, lower, upper, roll_power))
            else:
                await client.send_message(message.channel, '```fix\n%s rolls %d (%d-%d).\n```' % (
                    message.author.display_name, roll, lower, upper))

            if bet is not None and payoff is not False:
                if payoff > 0:
                    jewbot.update_balance(message.author.id, bet * payoff)
                    await client.send_message(message.channel, '%s<@%s> wins %s%s.' % (
                        jewbot.prefix, message.author.id, jewbot.int_fmt(bet * payoff), jewbot.currency_symbol))
                else:
                    await client.send_message(message.channel,
                                              '%s<@%s> loses his bet.' % (jewbot.prefix, message.author.id))
        elif message.content.startswith('/8ball '):
            await client.send_message(message.channel, magic_ball(message.author.id))
        elif message.content.startswith('/fortune'):
            msg = "<@%s>, your fortune for today:\n```%s\n```"
            await client.send_message(message.channel, msg % (message.author.id, fortune(message.author.id)))
        elif message.content.startswith('/help') or message.content.startswith('/commands'):
            help_message = """
`Available commands:`

**/help** - sends you this message
**/roll** *[[range_lower_limit-]range_upper_limit]* - rolls a random number within given range
**/default** *[[range_lower_limit-]range_upper_limit]* - sets default roll limits
**/8ball** - answers a yes/no question
**/avatar** *@someone* - posts *@someone*'s avatar in chat
**/choose** *option 1 or option 2 [or option 3 ...[or option n]]* - randomly chooses one of the given options
**/tell** *message* - posts anonymous message

**/balance** or **/assets** - displays your current balance and owned assets
**/buy** - shows the list of goods available for purchase
**/buy** *[amount]* *item_name* - buy specified *amount* of *item_name*
**/buy** **all** *item_name* - buy all of *item_name* you can afford
**/bet** - shows your current bet
**/bet** *amount* - bet on your next roll (if dubs - you win). If you already have an active bet - the *amount* is added to it. %d%% of the winnings goes to Eternal Jew.
**/bet** **all** - bet everything, surely you will win
**/br** *amount* - bet on your next roll (if dubs - you win) and roll immediately. If you already have an active bet - the *amount* is added to it. %d%% of the winnings goes to Eternal Jew.
**/br** **all** - bet everything and roll immediately, surely you will win
**/pay** *user* *amount* - pays specified *amount* to *user*

**/trivia** *[categories]* - asks a trivia question. You can win %s if you answer correctly.
**/categories** - sends you a list of available trivia categories

**/fortune** - tells your fortune for today

            """ % (jewbot.bet_win_cut * 100, jewbot.bet_win_cut * 100, jewbot.currency_symbol)
            await client.send_message(message.author, help_message)
            await client.send_message(message.channel, 'Sent commands description to you, <@%s>. ❤' % message.author.id)
        elif message.content.startswith('/avatar '):
            # try:
            #     cd = get_cd('avatar', message.author)
            #     if cd:
            #         if ignored[message.author] == 0:
            #             await client.send_message(message.channel,
            #                                       '```diff\n- Ability is not ready yet. (%d sec CD) -\n```' % cd)
            #             ignored[message.author] = 1
            #         return
            # except KeyError:
            #     pass
            match = re.search(r'<@\!?(\d+?)>', message.content)
            if not match:
                member = message.server.get_member_named(message.content[len('/avatar '):])
            else:
                member = message.server.get_member(match.group(1))
            if member is None:
                await client.send_message(message.channel, 'I don\'t know this guy, <@%s>.' % message.author.id)
                return
            try:
                http = urllib3.PoolManager(
                    cert_reqs='CERT_REQUIRED',
                    ca_certs=certifi.where()
                )
                r = http.request('GET', member.avatar_url, preload_content=False)
                if re.search(r'\.gif(\?.+)?$', member.avatar_url):
                    await client.send_file(message.channel, r, filename='%s.gif' % member.display_name)
                else:
                    img = Image.open(r).convert('RGBA')
                    tmp = io.BytesIO()
                    img.save(tmp, format='PNG')
                    tmp.seek(0)
                    # set_cd('avatar', message.author)
                    # ignored[message.author] = 0
                    await client.send_file(message.channel, tmp, filename='%s.png' % member.display_name)
            except:
                await client.send_message(message.channel, '%s doesn\'t have an avatar.' % member.display_name)
        elif message.content.startswith('/choose'):
            try:
                cd = get_cd('choose', message.author)
                if cd:
                    if ignored[message.author] == 0:
                        await client.send_message(message.channel,
                                                  '```diff\n- Ability is not ready yet. (%d sec CD) -\n```' % cd)
                        ignored[message.author] = 1
                    return
            except KeyError:
                pass
            choices = message.content[len('/choose '):].split(' or ')
            choice_count = len(choices)
            if choice_count < 2:
                await client.send_message(message.channel, 'Nothing to choose from, <@%s>.' % message.author.id)
            else:
                choice = random.randint(0, choice_count - 1)
                set_cd('choose', message.author)
                ignored[message.author] = 0
                await client.send_message(message.channel, '"%s", <@%s>.' % (choices[choice], message.author.id))
        elif message.content.startswith('/tell'):
            try:
                cd = get_cd('tell', message.author)
                if cd:
                    if ignored[message.author] == 0:
                        await client.send_message(message.channel,
                                                  '```diff\n- Ability is not ready yet. (%d sec CD) -\n```' % cd)
                        ignored[message.author] = 1
                    return
            except KeyError:
                pass
            if not message.channel.is_private or message.channel.user != message.author:
                await client.send_message(message.author,
                                          'Try here, <@%s>, otherwise it won\'t be anonymous.' % message.author.id)
                return
            anon_msg = message.content[len('/tell '):]
            if len(anon_msg) < 1:
                await client.send_message(message.channel, 'You should type in something, <@%s>.' % message.author.id)
            else:
                em = discord.Embed(description=anon_msg, colour=0x237f52)
                em.set_author(name='Anon says:', icon_url=client.user.default_avatar_url)
                set_cd('tell', message.author)
                ignored[message.author] = 0
                await client.send_message(client.get_channel(anon_msg_channel_id), embed=em)
        elif message.content.startswith('/balance') or message.content.startswith('/assets'):
            if message.channel.id != spam_channel_id:
                return
            account = jewbot.get_account(message.author.id)
            await client.send_message(message.channel,
                                      '%sYou have %s%s on your account, <@%s>.\n%s' % (jewbot.prefix, jewbot.int_fmt(account['balance']),
                                                                                     jewbot.currency_symbol,
                                                                                     message.author.id, jewbot.get_assets_list_msg(message.author.id)))
        elif message.content.startswith('/exactbalance'):
            if message.channel.id != spam_channel_id:
                return
            account = jewbot.get_account(message.author.id)
            await client.send_message(message.channel, '%f' % account['balance'])
        elif message.content.startswith('/bet'):
            if message.channel.id != spam_channel_id:
                return
            account = jewbot.get_account(message.author.id)
            args = message.content.strip().split(' ')[1:]
            amount = 0
            current_bet = jewbot.get_bet(message.author.id)
            if len(args) < 1:
                if current_bet is None:
                    await client.send_message(message.channel,
                                              '%sYou need to specify the bet amount, <@%s>.' % (
                                                  jewbot.prefix, message.author.id))
                else:
                    await client.send_message(message.channel,
                                              '%sYour current bet is %s%s, <@%s>.' % (
                                                  jewbot.prefix, jewbot.int_fmt(current_bet), jewbot.currency_symbol, message.author.id))
                return
            if args[0].lower() == 'all':
                amount = int(account['balance'])
            else:
                try:
                    amount = int(args[0])
                except ValueError:
                    pass
            if amount < 1:
                await client.send_message(message.channel,
                                          '%sYou need to specify the bet amount, <@%s>.' % (
                                              jewbot.prefix, message.author.id))
                return
            current_bet = jewbot.get_bet(message.author.id)
            if jewbot.bet(message.author.id, amount) is False:
                await client.send_message(message.channel,
                                          '%sYou don\'t have enough to bet that amount, <@%s>.' % (
                                              jewbot.prefix, message.author.id))
                return
            if current_bet is None:
                await client.send_message(message.channel,
                                          '%s<@%s> bets %s%s on the next roll.' % (
                                              jewbot.prefix, message.author.id, jewbot.int_fmt(amount), jewbot.currency_symbol))
            else:
                await client.send_message(message.channel,
                                          '%s<@%s> increases his bet on the next roll by %s%s. New bet is %s%s.' % (
                                              jewbot.prefix, message.author.id, jewbot.int_fmt(amount), jewbot.currency_symbol,
                                              jewbot.int_fmt(amount + current_bet), jewbot.currency_symbol))
        elif message.content.startswith('/br'):
            if message.channel.id != spam_channel_id:
                return
            account = jewbot.get_account(message.author.id)
            args = message.content.strip().split(' ')[1:]
            amount = 0
            current_bet = jewbot.get_bet(message.author.id)
            skip_to_roll = False
            msg = ''
            if len(args) < 1:
                if current_bet is None:
                    await client.send_message(message.channel,
                                              '%sYou need to specify the bet amount, <@%s>.' % (
                                                  jewbot.prefix, message.author.id))
                    return
                else:
                    skip_to_roll = True
            if not skip_to_roll:
                if args[0].lower() == 'all':
                    amount = int(account['balance'])
                else:
                    try:
                        amount = int(args[0])
                    except ValueError:
                        pass
                if amount < 1:
                    await client.send_message(message.channel,
                                              '%sYou need to specify the bet amount, <@%s>.' % (
                                                  jewbot.prefix, message.author.id))
                    return
                current_bet = jewbot.get_bet(message.author.id)
                if jewbot.bet(message.author.id, amount) is False:
                    await client.send_message(message.channel,
                                              '%sYou don\'t have enough to bet that amount, <@%s>.' % (
                                                  jewbot.prefix, message.author.id))
                    return
                if current_bet is None:
                    msg += '%s<@%s> bets %s%s on the next roll.\n' % (jewbot.prefix, message.author.id, jewbot.int_fmt(amount), jewbot.currency_symbol)
                else:
                    msg += '%s<@%s> increases his bet on the next roll by %s%s. New bet is %s%s.\n' % (jewbot.prefix, message.author.id, jewbot.int_fmt(amount), jewbot.currency_symbol,
                                                  jewbot.int_fmt(amount + current_bet), jewbot.currency_symbol)
            try:
                cd = get_cd('roll', message.author)
                if cd:
                    if ignored[message.author] == 0:
                        msg += '```diff\n- Ability is not ready yet. (%d sec CD) -\n```\n' % cd
                        ignored[message.author] = 1
                    return
            except KeyError:
                pass
            if message.author.id in default_roll:
                lower = default_roll[message.author.id]['lower']
                upper = default_roll[message.author.id]['upper']
            else:
                lower = 1
                upper = 100
            random.seed()
            roll = random.randint(lower, upper)
            bet = jewbot.get_bet(message.author.id)
            payoff = 0
            if bet is not None:
                payoff = jewbot.get_payoff(lower, upper, roll)
                if payoff is not False:
                    jewbot.clear_bet(message.author.id)
            if message.channel.id != spam_channel_id:
                set_cd('roll', message.author)
            ignored[message.author] = 0
            roll_power = get_dubs_power(roll, lower, upper)
            if roll_power is not None:
                msg += '```md\n[%s rolls %d (%d-%d).][%s]\n```' % (message.author.display_name, roll, lower, upper, roll_power)
            else:
                msg += '```fix\n%s rolls %d (%d-%d).\n```' % (message.author.display_name, roll, lower, upper)
            if bet is not None and payoff is not False:
                if payoff > 0:
                    jewbot.update_balance(message.author.id, bet * payoff)
                    msg += '%s<@%s> wins %s%s.' % (jewbot.prefix, message.author.id, jewbot.int_fmt(bet * payoff), jewbot.currency_symbol)
                else:
                    msg += '%s<@%s> loses his bet.' % (jewbot.prefix, message.author.id)
            await client.send_message(message.channel, msg)
        elif message.content.startswith('/buy'):
            if message.channel.id != spam_channel_id:
                return
            args = message.content.strip().split(' ', 2)[1:]
            amount = 1
            if len(args) < 1:
                await client.send_message(message.channel, jewbot.get_assets_types_msg())
                return
            if len(args) > 1:
                if args[0].lower() == 'all':
                    account = jewbot.get_account(message.author.id)
                    asset_id = jewbot.find_asset(args[1])
                    if asset_id is not None and jewbot.asset_types[asset_id]['price'] < account['balance']:
                        amount = int(account['balance'] / jewbot.asset_types[asset_id]['price'])
                        if amount < 1:
                            amount = 1
                else:
                    try:
                        amount = int(args[0])
                        if amount < 1:
                            amount = 1
                        asset_id = jewbot.find_asset(args[1])
                    except ValueError:
                        asset_id = jewbot.find_asset(' '.join(args))
            else:
                asset_id = jewbot.find_asset(' '.join(args))
            if asset_id is None:
                await client.send_message(message.channel, jewbot.get_assets_types_msg())
                return
            if jewbot.buy(message.author.id, asset_id, amount):
                await client.send_message(message.channel,
                                          '%s<@%s> bought %s "%s" for %s%s.' % (
                                              jewbot.prefix, message.author.id, jewbot.int_fmt(amount),
                                              jewbot.asset_types[asset_id]['name'],
                                              jewbot.int_fmt(jewbot.asset_types[asset_id]['price'] * amount), jewbot.currency_symbol))
            else:
                print(message.author)
                print('amount = ', amount)
                print('balance = ', account['balance'])
                print('price = ', jewbot.asset_types[asset_id]['price'])
                print(account['balance'], ' < ', jewbot.asset_types[asset_id]['price'] * amount, ' is ', account['balance'] < jewbot.asset_types[asset_id]['price'] * amount)
                await client.send_message(message.channel,
                                          '%sYou don\'t have enough to afford that, <@%s>.' % (
                                              jewbot.prefix, message.author.id))
        elif message.content.startswith('/pay'):
            args = message.content.strip().split(' ', 1)[1:]
            format_err_msg = '%sYou need to specify recipient and amount, <@%s>.' % (jewbot.prefix, message.author.id)
            if len(args) > 0:
                args = args[0].rsplit(' ', 1)
            else:
                await client.send_message(message.channel, format_err_msg)
                return
            if len(args) < 2:
                await client.send_message(message.channel, format_err_msg)
                return
            amount = 0
            try:
                amount = int(args[1])
            except ValueError:
                pass
            if amount < 1:
                await client.send_message(message.channel, format_err_msg)
                return
            match = re.search(r'<@\!?(\d+?)>', args[0])
            if not match:
                member = message.server.get_member_named(args[0])
            else:
                member = message.server.get_member(match.group(1))
            if member is None:
                await client.send_message(message.channel,
                                          '%sI don\'t know this goy, <@%s>.' % (jewbot.prefix, message.author.id))
                return
            if message.author.id == member.id:
                await client.send_message(message.channel, format_err_msg)
                return
            if jewbot.pay(message.author.id, member.id, amount):
                await client.send_message(message.channel,
                                          '%s<@%s> pays <@%s> %s%s.' % (
                                          jewbot.prefix, message.author.id, member.id, jewbot.int_fmt(amount), jewbot.currency_symbol))
            else:
                await client.send_message(message.channel,
                                          '%sYou don\'t have enough to afford that, <@%s>.' % (
                                              jewbot.prefix, message.author.id))
        elif message.content.startswith('/trivia'):
            if message.channel.id in active_questions:
                return
            args = message.content.strip().split(' ', 1)[1:]
            categories = []
            if len(args) > 0 and args[0].lower() not in ['any', 'all']:
                categories = triviabot.find_categories(args[0])
                if len(categories) < 1:
                    await client.send_message(message.channel, 'Couldn\'t find that category, <@%s>.' % message.author.id)
                    return
            if triviabot.token is None:
                triviabot.update_token()
            question = triviabot.get_question(categories)
            asyncio.ensure_future(start_trivia(message.channel.id, question))
        elif message.content.startswith('/categories'):
            msg = 'Available trivia categories:\n'
            for cat_id in triviabot.categories:
                msg += ' - "%s"\n' % triviabot.categories[cat_id]
            await client.send_message(message.author, msg)
            await client.send_message(message.channel, 'Sent trivia categories to you, <@%s>.' % message.author.id)
    except:
        if message.author != client.user:
            await client.send_message(message.channel, 'System error! Send help!\n\nX___X')
        raise


def magic_ball(user_id):
    answers = [
        'It is certain, <@%s>.',
        'It is decidedly so, <@%s>.',
        'Without a doubt, <@%s>.',
        'Yes, <@%s>, definitely.',
        'You may rely on it, <@%s>.',
        'As I see it, yes, <@%s>.',
        'Most likely, <@%s>.',
        'Outlook good, <@%s>.',
        'Yes, <@%s>.',
        'Signs point to yes, <@%s>.',
        # 'Reply hazy try again, <@%s>.',
        # 'Ask again later, <@%s>.',
        # 'Better not tell you now, <@%s>.',
        # 'Cannot predict now, <@%s>.',
        # 'Concentrate and ask again, <@%s>.',
        'Don\'t count on it, <@%s>.',
        'My reply is no, <@%s>.',
        'My sources say no, <@%s>.',
        'Outlook not so good, <@%s>.',
        'Very doubtful, <@%s>.'
    ]
    return answers[random.randint(0, len(answers) - 1)] % user_id


def fortune(user_id):
    date = time.strftime("S@lt1!(for reasons)%Y%m%d")
    random.seed(date.join(user_id))
    answers = [
        # Spades
        'Sickness of a friend. Go at once!',
        'Great disappointment.',
        'Look out for trouble within a few days.',
        'A scandal will be barely escaped.',
        'A false friend. Beware.',
        'Do not talk too much - listen.',
        'You have a few trustworthy friends and one unsuspected enemy.',
        'You will shortly occupy a strange bed.',
        'Your business will be poor for a short time.',
        'You will hear something unpleasant.',
        'You know him - but not as well as you think.',
        'A friend is false - but keep your own counsel.',
        'Forgive - but do not trust again.',
        'Death of a friend.',
        'A sudden journey.',
        'Guests coming. Means trouble.',
        'You will hear of a wedding and be disappointed.',
        'Be careful of a dark, elderly man.',
        'You will be invited to a party. Think, before you accept!',
        'A dark woman is trying to get you into trouble.',
        'Be cheerful - no matter what happens.',
        'A business disappointment unless you proceed cautiously.',
        'Pay no attention to something you are going to hear.',
        'No matter what he says, don\'t trust him.',
        'A pretty woman wants to see you. Avoid her.',
        'A present will be offered to you. Refuse it.',
        # Hearts
        'You will soon have cause to forget your money troubles.',
        'Your next love affair will surprise you.',
        'You are going to move to a new house.',
        'A wedding in the near future.',
        'You have been wishing for something. Do not give up hope.',
        'Do not wait too long before saying "Yes".',
        'Be guided by this number - 7.',
        'You have people near you who are not true.',
        'Be careful in your business dealings for the next few days.',
        'Happiness from an unexpected source.',
        'Be very kind when you meet your newest friend.',
        'Be very, very careful when you see a certain blonde.',
        'You will soon meet the one you most want to meet.',
        'A serious quarrel. Reconciliation depends on you.',
        'Good luck will be with you early in the month.',
        'The one who cares for you is anxious for a letter.',
        'You are going to marry more than once.',
        'You are not shrewd enough.',
        'A long motor trip - with a surprise at the end.',
        'This is your lucky number - 7.',
        'A woman is coming between you and your beloved.',
        'Good luck coming to you.',
        'A change in the life of a true friend.',
        'You are continually in someone\'s thoughts.',
        'A woman will be the cause of contentment for you soon.',
        'A letter. Act on it at once.',
        # Clubs
        'A short trip coming. Important.',
        'Good news in two weeks.',
        'You are going to marry sooner than you expect.',
        'Marriage ahead.',
        'A meeting soon with someone who will be interested in you.',
        'Money coming to you - but a little trouble about it.',
        'Live your own life.',
        'Next winter you will go on a long trip.',
        'You have many friends. But one is not loyal to you.',
        'Money is going to be willed to you',
        'The one you marry will bring you wealth.',
        'A jealous woman.',
        'Do not give him any hope.',
        'A present.',
        'A surprise.',
        'You have long been loved by the one you least suspect.',
        'Good business in sight.',
        'You will soon go on a long trip.',
        'Your troubles will vanish. Happiness ahead.',
        'Do not let talk of jealous persons bother you.',
        'A relative is going to be ill, but will recover.',
        'A big surprise coming to you.',
        'Keep up your courage a little longer. Better things in sight for you.',
        'Your life\'s romance is about to begin.',
        'A woman is going to tell a lie that will hurt you.',
        'You need self confidence. Otherwise you will lose.',
        # Diamonds
        'A ring.',
        'Small sum of money coming to you.',
        'Pleasant news is coming to you.',
        'A wedding dress.',
        'A pleasant surprise.',
        'A stranger will ask you to the theatre. Accept.',
        'A long trip in the near future.',
        'A turn for the better.',
        'Your wish.',
        'Wealth beyond your fondest dreams.',
        'An engagement will be broken because of you.',
        'A woman will soon invite your to her home. Go!',
        'A new friend will mean the turning point in your life.',
        'An important letter.',
        'An enjoyable trip for you soon.',
        'You owe someone a letter. Write it at once.',
        'A conference that will benefit you.',
        'A dinner invitation.',
        'A stranger who will turn into a good friend.',
        'You want money. Be patient.',
        'You will sell something and get a good price.',
        'Your wish.',
        'Good luck.',
        'You are going to be happier than you dared hope.',
        'The best friend you have will help you.',
        'A man is working to make things come out right for you.'
    ]
    answer = answers[random.randint(0, len(answers) - 1)]
    random.seed()
    return answer


def set_cd(ability, user_id):
    timestamp = int(time.time())
    try:
        cooldowns[ability]
    except KeyError:
        cooldowns[ability] = {}
    cooldowns[ability][user_id] = timestamp


def get_cd(ability, user_id):
    timestamp = int(time.time())
    cooldown = default_cd
    try:
        cooldowns[ability]
    except KeyError:
        cooldowns[ability] = {}
    try:
        cooldown = ability_cds[ability]
    except KeyError:
        pass
    if timestamp - cooldowns[ability][user_id] < cooldown:
        return cooldown - (timestamp - cooldowns[ability][user_id])
    else:
        return False


def get_dubs_power(roll, lower, upper):
    if roll < 10 and upper - lower >= 99:
        return dubs_power_str[1]
    n = 1
    div = 1
    scale = 10 ** n
    while (roll % scale) % div == 0:
        n += 1
        div = 1
        scale = 10 ** n
        for i in range(1, n):
            div = div * 10 + 1
    if n > 7:
        n = 7
    if upper - lower >= (scale / 10 - 1) and n > 2:
        return dubs_power_str[n - 1]
    else:
        return dubs_power_str[(n - 1) * 10]


async def start_trivia(channel_id: int, question: triviabot.TriviaQuestion):
    if channel_id in active_questions:
        return
    msg = '**Category:** %s\n**Difficulty**: %s\n**Time to answer**: %d seconds\n\n' % (
        question.category, question.difficulty, answer_time
    )
    msg += '**Question:**\n"%s"\n\n**Answers:**\n' % question.question
    for option in question.answers:
        msg += '"%s"\n' % option
    channel = client.get_channel(channel_id)
    await client.send_message(channel, msg)
    active_questions[channel_id] = {'question': question, 'answers': {}}
    await asyncio.sleep(answer_time)
    answers = active_questions[channel_id]['answers']
    winners = ''
    winners_count = 0
    win_amount = default_win * question.difficulty.value
    del active_questions[channel_id]
    for user_id in answers:
        if question.is_correct_answer(answers[user_id]):
            winners_count += 1
            winners += '<@%s>, ' % user_id
            jewbot.update_balance(user_id, win_amount)
    winners = winners[:-2]
    msg = '**Time is up! Correct answer:** "%s"\n' % question.correct_answer
    if winners_count < 1:
        msg += 'Nobody guessed correctly.'
    elif winners_count > 1:
        msg += '%s get %d%s each.' % (winners, win_amount, jewbot.currency_symbol)
    else:
        msg += '%s gets %d%s.' % (winners, win_amount, jewbot.currency_symbol)
    await client.send_message(channel, msg)


def reg_answer(channel_id, user_id, answer):
    if channel_id in active_questions:
        if user_id not in active_questions[channel_id]['answers']:
            active_questions[channel_id]['answers'][user_id] = answer

client.run(prod_token)
