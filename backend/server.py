"""
Datenanalyse-Dashboard(UK/FR/DE/IT) - 统一服务器
前端: http://localhost:5003
后端API: http://localhost:5003/api/*
"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import json
from datetime import datetime, timedelta
import os
import time

# ============ 配置 ============
def read_env(name, default=''):
    value = os.getenv(name)
    if value:
        return value
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
                return winreg.QueryValueEx(key, name)[0] or default
        except OSError:
            pass
    return default

PORT = int(read_env('FB_REPORT_PORT', os.getenv('PORT', '5003')))

CONFIG = {
    'app_id': read_env('FB_APP_ID', '2254877108592549'),
    'app_secret': read_env('FB_APP_SECRET'),
    'access_token': read_env('FB_ACCESS_TOKEN'),
    'business_id': read_env('FB_BUSINESS_ID', '303627654972252'),
    'ad_accounts': {
        '英国站': {'id': '1450908062157108', 'page': 'SUNLU UK'},
        '法国站': {'id': '1263004614711858', 'page': 'SUNLU FR'},
        '德国站': {'id': '567253999563537', 'page': 'SUNLU.DE.WEZO'},
        '意大利站': {'id': '2194106121024447', 'page': 'SUNLU IT'}
    }
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, 'fb_ads_data.json')
CONFIG_FILE = os.path.join(BASE_DIR, 'user_config.json')  # 用户配置文件
AUDIENCE_FILE = os.path.join(BASE_DIR, 'fb_audience_data.json')  # 受众分析缓存
AUDIENCE_CACHE_DIR = os.path.join(BASE_DIR, 'fb_audience_cache')  # 按天缓存目录

# 转化广告专属过滤
NON_CONVERSION = ["REACH","BRAND_AWARENESS","TRAFFIC","VIDEO_VIEWS","POST_ENGAGEMENT","APP_INSTALLS","AWARENESS","ENGAGEMENT","EVENT_RESPONSES","PAGE_LIKES"]

CONV_CAMPAIGN_CACHE = {}  # {act_id: {'ids': [...], 'ts': timestamp}}

def get_conversion_campaign_ids(act_id, access_token):
    """获取转化类系列ID列表（排除流量/曝光/互动，1小时缓存）"""
    import time as _time
    entry = CONV_CAMPAIGN_CACHE.get(act_id)
    if entry and (_time.time() - entry.get('ts', 0)) < 3600:
        print(f"  [系列缓存] {act_id} 命中 {len(entry['ids'])} 个")
        return entry['ids']
    
    print(f"  [系列列表] {act_id} 从FB获取...")
    all_ids = []
    url = f'https://graph.facebook.com/v22.0/act_{act_id}/campaigns'
    params = {
        'access_token': access_token,
        'fields': 'id,objective,status',
        'filtering': json.dumps([{"field":"objective","operator":"NOT_IN","value":NON_CONVERSION}]),
        'limit': 500
    }
    next_url = url
    for _ in range(5):
        resp = requests.get(next_url, params=params if next_url == url else None)
        data = resp.json()
        if 'error' in data:
            print(f"    Error: {data['error'].get('message')}")
            break
        for c in data.get('data', []):
            if c.get('status') != 'DELETED':
                all_ids.append(c['id'])
        paging = data.get('paging', {})
        next_url = paging.get('next')
        if not next_url:
            break
        params = None
    
    CONV_CAMPAIGN_CACHE[act_id] = {'ids': all_ids, 'ts': _time.time()}
    print(f"    {len(all_ids)} 个转化系列")
    return all_ids

def ensure_cache_dir():
    os.makedirs(AUDIENCE_CACHE_DIR, exist_ok=True)

def _safe_site(site):
    return site.replace(' ', '_').replace('/', '_').replace('\\', '_')

def _aud_day_path(site, date_str):
    return os.path.join(AUDIENCE_CACHE_DIR, f'aud_{_safe_site(site)}_{date_str}.json')

def _ct_day_path(site, date_str):
    return os.path.join(AUDIENCE_CACHE_DIR, f'ct_{_safe_site(site)}_{date_str}.json')

def date_range_days(since, until):
    """生成日期范围内的所有日期列表"""
    s = datetime.strptime(since, '%Y-%m-%d')
    u = datetime.strptime(until, '%Y-%m-%d')
    days = []
    while s <= u:
        days.append(s.strftime('%Y-%m-%d'))
        s += timedelta(days=1)
    return days

def data_dates_for_range(all_data, start_date, end_date):
    dates = set()
    for key in ['conversion', 'traffic']:
        for c in all_data.get(key, {}).get('campaigns', []):
            d = c.get('date', '')
            if start_date <= d <= end_date:
                dates.add(d)
    return sorted(dates)

# ============ 统一Flask应用 (端口5003) ============
app = Flask(__name__)
CORS(app)

def facebook_config_error():
    missing = [name for name, key in (
        ('FB_APP_SECRET', 'app_secret'),
        ('FB_ACCESS_TOKEN', 'access_token')
    ) if not CONFIG.get(key)]
    if missing:
        return 'Missing Facebook config: ' + ', '.join(missing)
    return ''

def get_campaigns_insights(account_id, start_date, end_date, access_token):
    """获取广告系列级别成效数据（支持分页）"""
    url = f'https://graph.facebook.com/v19.0/act_{account_id}/insights'
    params = {
        'access_token': access_token,
        'fields': 'campaign_name,spend,impressions,clicks,actions,action_values',
        'time_range': json.dumps({'since': start_date, 'until': end_date}),
        'level': 'campaign',
        'time_increment': 1,
        'limit': 500
    }
    
    all_data = []
    next_url = url
    current_params = params
    
    while next_url:
        resp = requests.get(next_url, params=current_params)
        data = resp.json()
        
        if 'error' in data:
            return data  # 返回错误，由上层重试
        
        items = data.get('data', [])
        all_data.extend(items)
        
        # 检查是否有下一页
        paging = data.get('paging', {})
        next_url = paging.get('next')
        current_params = None
    
    return {'data': all_data}

def sync_one_site(name, account_id, start_date, end_date, access_token, all_data, traffic_keywords, max_retries=3):
    """同步单个站点数据，支持重试"""
    for attempt in range(max_retries):
        if attempt > 0:
            wait = 10 * attempt  # 10s, 20s, 30s
            print(f"  [{name}] 第{attempt+1}次重试，等待{wait}秒...")
            time.sleep(wait)
        
        campaigns_data = get_campaigns_insights(account_id, start_date, end_date, access_token)
        
        if 'error' in campaigns_data:
            err_msg = campaigns_data['error'].get('message', 'Unknown')
            err_code = campaigns_data['error'].get('code', 0)
            print(f"  [{name}] 错误(code={err_code}): {err_msg}")
            
            # 可重试的错误
            if err_code in (2, 4, 17, 32, 613) and attempt < max_retries - 1:
                continue
            # 不可重试，返回错误
            return None, f"{name}: {err_msg}"
        
        # 成功获取数据
        break
    
    if 'error' in campaigns_data:
        return None, f"{name}: 重试{max_retries}次后仍然失败"
    
    # 处理获得的广告数据
    existing_conv_campaigns = all_data['conversion'].get('campaigns', [])
    existing_traffic_campaigns = all_data['traffic'].get('campaigns', [])
    
    existing_keys = set()
    for c in existing_conv_campaigns:
        existing_keys.add(f"{c.get('siteName', '')}|{c.get('date', '')}|{c.get('campaign', '')}")
    for c in existing_traffic_campaigns:
        existing_keys.add(f"{c.get('siteName', '')}|{c.get('date', '')}|{c.get('campaign', '')}")
    
    site_new = 0
    site_skip = 0
    new_conv = []
    new_traffic = []
    
    for item in campaigns_data.get('data', []):
        daily_record = parse_insight_item(item)
        daily_record['siteName'] = name
        
        record_key = f"{name}|{daily_record['date']}|{daily_record['campaign']}"
        if record_key in existing_keys:
            site_skip += 1
            continue
        
        site_new += 1
        existing_keys.add(record_key)
        
        campaign_name = item.get('campaign_name', '').lower()
        if any(kw in campaign_name for kw in traffic_keywords):
            new_traffic.append(daily_record)
        else:
            new_conv.append(daily_record)
    
    all_data['conversion']['campaigns'].extend(new_conv)
    all_data['traffic']['campaigns'].extend(new_traffic)
    
    print(f"  [{name}] 新增: {len(new_conv)} 条转化, {len(new_traffic)} 条流量, 跳过: {site_skip} 条重复")
    
    return {'conv': len(new_conv), 'traffic': len(new_traffic), 'skip': site_skip}, None

def load_existing_data():
    """加载已有数据"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_data(data):
    """保存数据到文件"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_insight_item(item):
    """解析单条FB API返回的insight数据"""
    day_spend = float(item.get('spend', 0))
    day_impressions = int(item.get('impressions', 0))
    day_clicks = int(item.get('clicks', 0))
    day_purchases = 0
    day_purchase_value = 0
    
    actions = item.get('actions', [])
    action_values = item.get('action_values', [])
    
    purchase_action_types = ['purchase', 'omni_purchase', 'web_in_store_purchase', 'onsite_purchase']
    purchase_value_types = ['purchase_value', 'omni_purchase_value', 'onsite_web_app_purchase', 'onsite_web_purchase', 'web_in_store_purchase_value']
    
    for a in actions:
        action_type = a.get('action_type', '')
        if any(pt in action_type for pt in purchase_action_types):
            try: day_purchases += int(float(a.get('value', 0)))
            except: pass
            break
    
    for av in action_values:
        action_type = av.get('action_type', '')
        if any(pt in action_type for pt in purchase_value_types) or 'purchase' in action_type:
            try: day_purchase_value += float(av.get('value', 0))
            except: pass
            break
    
    day_ctr = (day_clicks / day_impressions * 100) if day_impressions > 0 else 0
    day_cpa = (day_spend / day_purchases) if day_purchases > 0 else 0
    day_roi = (day_purchase_value / day_spend) if day_spend > 0 else 0
    day_cvr = (day_purchases / day_clicks * 100) if day_clicks > 0 else 0
    
    return {
        'date': item.get('date_start', ''),
        'campaign': item.get('campaign_name', 'Unknown'),
        'spend': round(day_spend, 2),
        'impressions': day_impressions,
        'clicks': day_clicks,
        'purchases': day_purchases,
        'purchase_value': round(day_purchase_value, 2),
        'ctr': round(day_ctr, 2),
        'cpa': round(day_cpa, 2),
        'roi': round(day_roi, 2),
        'cvr': round(day_cvr, 2)
    }

def summarize_daily(daily_list):
    """汇总每日数据"""
    if not daily_list: return None
    total = {'spend': 0, 'sales': 0, 'conversions': 0, 'clicks': 0, 'impressions': 0}
    for d in daily_list:
        total['spend'] += d.get('spend', 0)
        total['sales'] += d.get('sales', 0) or d.get('purchase_value', 0)
        total['conversions'] += d.get('conversions', 0) or d.get('purchases', 0)
        total['clicks'] += d.get('clicks', 0)
        total['impressions'] += d.get('impressions', 0)
    
    days = len(daily_list)
    if days == 0: return None
    total['cpa'] = total['conversions'] > 0 and total['spend'] / total['conversions'] or 0
    total['roi'] = total['spend'] > 0 and total['sales'] / total['spend'] or 0
    total['ctr'] = total['impressions'] > 0 and (total['clicks'] / total['impressions'] * 100) or 0
    total['cvr'] = total['clicks'] > 0 and (total['conversions'] / total['clicks'] * 100) or 0
    total['days'] = days
    for k in ['spend', 'sales', 'cpa', 'roi', 'ctr', 'cvr']:
        total[k] = round(total[k], 2)
    return total

def build_site_summary(daily_records):
    """从每日记录构建站点汇总数据"""
    if not daily_records:
        return None
    
    summary = summarize_daily(daily_records)
    if not summary:
        return None
    
    return {
        'daily_data': daily_records,
        'spend': summary['spend'],
        'sales': summary['sales'],
        'conversions': summary['conversions'],
        'cpa': summary['cpa'],
        'roi': summary['roi'],
        'clicks': summary['clicks'],
        'impressions': summary['impressions'],
        'ctr': summary['ctr'],
        'cvr': summary['cvr']
    }

# ============ 同步进度追踪 (线程安全) ============
import threading
_sync_lock = threading.Lock()
_sync_progress = {'status': 'idle', 'message': '', 'site': '', 'site_idx': 0, 'total_sites': 4,
                   'chunk': '', 'chunk_idx': 0, 'total_chunks': 0, 'errors': [], 
                   'new_records': 0, 'logs': []}

def _update_progress(**kwargs):
    with _sync_lock:
        _sync_progress.update(kwargs)
        _sync_progress['last_update'] = time.time()

def _add_log(msg):
    with _sync_lock:
        _sync_progress['logs'].append(msg)
        if len(_sync_progress['logs']) > 50:
            _sync_progress['logs'] = _sync_progress['logs'][-50:]

CHUNK_DAYS = 3  # 每次请求最多3天数据，避免FB限流

def _gen_chunks(since, until):
    """生成日期分块"""
    s = datetime.strptime(since, '%Y-%m-%d')
    e = datetime.strptime(until, '%Y-%m-%d')
    chunks = []
    cur = s
    while cur <= e:
        chunk_end = min(cur + timedelta(days=CHUNK_DAYS - 1), e)
        chunks.append((cur.strftime('%Y-%m-%d'), chunk_end.strftime('%Y-%m-%d')))
        cur = chunk_end + timedelta(days=1)
    return chunks

def _fetch_chunk_with_retry(act_id, chunk_start, chunk_end, access_token, site_name, max_retries=4):
    """获取单个日期块数据，支持重试"""
    for attempt in range(max_retries):
        if attempt > 0:
            wait = 12 * (attempt + 1)
            _add_log(f"{site_name} {chunk_start}~{chunk_end} 第{attempt+1}次重试(等待{wait}s)...")
            time.sleep(wait)
        
        result = get_campaigns_insights(act_id, chunk_start, chunk_end, access_token)
        
        if 'error' not in result:
            return result
        
        err = result['error']
        err_code = err.get('code', 0)
        _add_log(f"{site_name} {chunk_start}~{chunk_end} 错误(code={err_code}): {err.get('message','?')}")
        
        # 可重试的错误码
        if err_code in (2, 4, 17, 32, 613, 80000) and attempt < max_retries - 1:
            continue
        return result
    
    return result

# ============ API路由 ============
@app.route('/api/sync', methods=['POST'])
def sync_data():
    """同步 Facebook Ads 数据，分块请求 + 增量更新"""
    global _sync_progress
    
    data = request.json or {}
    
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    force_refresh_days = int(data.get('force_refresh_days', 0))  # 清除最近N天旧数据重新同步
    
    if not start_date or not end_date:
        return jsonify({'success': False, 'message': '请提供 start_date 和 end_date'})
    
    config_error = facebook_config_error()
    if config_error:
        return jsonify({'success': False, 'message': config_error}), 500

    access_token = CONFIG['access_token']
    traffic_keywords = ['流量', 'traffic', 'trafic', '曝光', 'reach']
    
    # 初始化进度
    chunks = _gen_chunks(start_date, end_date)
    sites = list(CONFIG['ad_accounts'].items())
    _update_progress(
        status='running', message='开始同步...', site='', site_idx=0, total_sites=len(sites),
        chunk='', chunk_idx=0, total_chunks=len(chunks), errors=[], new_records=0,
        logs=[f'日期范围: {start_date} ~ {end_date}', f'分{len(chunks)}块: {chunks}']
    )
    
    # 加载已有数据
    existing = load_existing_data()
    if existing:
        all_data = existing
        for key in ['conversion', 'traffic']:
            if key not in all_data:
                all_data[key] = {'sites': {}, 'summary': {}, 'campaigns': []}
            if 'campaigns' not in all_data[key]:
                all_data[key]['campaigns'] = []
    else:
        all_data = {
            'conversion': {'sites': {}, 'summary': {}, 'campaigns': []},
            'traffic': {'sites': {}, 'summary': {}, 'campaigns': []}
        }
    
    all_data['sync_time'] = datetime.now().isoformat()
    all_data['date_range'] = {'start': start_date, 'end': end_date}
    
    # 强制刷新：清除最近N天的旧数据，确保重新获取
    removed_count = 0
    if force_refresh_days > 0 and existing:
        from datetime import datetime as dt, timedelta
        cutoff = (dt.now() - timedelta(days=force_refresh_days)).strftime('%Y-%m-%d')
        for key in ['conversion', 'traffic']:
            old_count = len(all_data[key].get('campaigns', []))
            all_data[key]['campaigns'] = [
                c for c in all_data[key].get('campaigns', [])
                if str(c.get('date', '')).startswith('20') and c.get('date', '') < cutoff
            ]
            removed_count += old_count - len(all_data[key].get('campaigns', []))
        if removed_count > 0:
            msg = f'已清除最近{force_refresh_days}天旧数据 {removed_count} 条，将重新获取'
            _add_log(f'  ⚡ {msg}')
            print(f'  [强制刷新] {msg}')
    
    new_records = 0
    skipped_records = 0
    fb_errors = []
    
    for si, (name, info) in enumerate(sites):
        _update_progress(site=name, site_idx=si + 1, 
                         message=f'同步 {name} ({si+1}/{len(sites)})')
        _add_log(f'开始同步 {name}...')
        print(f"\n[{name}] 正在同步 {start_date} 至 {end_date}...")
        
        site_has_data = False
        
        for ci, (chunk_start, chunk_end) in enumerate(chunks):
            _update_progress(chunk=f'{chunk_start}~{chunk_end}', chunk_idx=ci + 1,
                             message=f'{name}: {chunk_start}~{chunk_end} ({ci+1}/{len(chunks)})')
            
            result = _fetch_chunk_with_retry(
                info['id'], chunk_start, chunk_end, access_token, name, max_retries=4
            )
            
            if 'error' in result:
                err_msg = result['error'].get('message', 'Unknown')
                fb_errors.append(f"{name} {chunk_start}~{chunk_end}: {err_msg}")
                _add_log(f"  ✗ {name} {chunk_start}~{chunk_end} 失败: {err_msg}")
                continue
            
            items = result.get('data', [])
            _add_log(f"  ✓ {name} {chunk_start}~{chunk_end}: 获取 {len(items)} 条")
            
            # 构建去重key集合
            exist_keys = set()
            for c in all_data['conversion']['campaigns']:
                exist_keys.add(f"{c.get('siteName','')}|{c.get('date','')}|{c.get('campaign','')}")
            for c in all_data['traffic']['campaigns']:
                exist_keys.add(f"{c.get('siteName','')}|{c.get('date','')}|{c.get('campaign','')}")
            
            new_conv = []
            new_traffic = []
            chunk_skip = 0
            
            for item in items:
                daily = parse_insight_item(item)
                daily['siteName'] = name
                
                rkey = f"{name}|{daily['date']}|{daily['campaign']}"
                if rkey in exist_keys:
                    chunk_skip += 1
                    continue
                exist_keys.add(rkey)
                site_has_data = True
                
                cn = item.get('campaign_name', '').lower()
                if any(kw in cn for kw in traffic_keywords):
                    new_traffic.append(daily)
                else:
                    new_conv.append(daily)
            
            all_data['conversion']['campaigns'].extend(new_conv)
            all_data['traffic']['campaigns'].extend(new_traffic)
            new_records += len(new_conv) + len(new_traffic)
            skipped_records += chunk_skip
            
            _update_progress(new_records=new_records)
            _add_log(f"    +{len(new_conv)}转化 +{len(new_traffic)}流量 (跳过{chunk_skip}重复)")
            
            # 每个chunk后保存
            save_data(all_data)
            
            # 块间短暂间隔
            time.sleep(1.5)
        
        if not site_has_data and any(e.startswith(name) for e in fb_errors):
            _add_log(f"  {name} 所有数据块获取失败")
        
        _add_log(f'  {name} 完成')
    
    # 重建站点汇总
    _update_progress(message='计算汇总数据...', chunk='汇总', chunk_idx=len(chunks))
    _add_log('计算站点汇总...')
    
    rebuild_summaries(all_data, CONFIG['ad_accounts'].keys())
    
    save_data(all_data)

    requested_dates = date_range_days(start_date, end_date)
    synced_dates = data_dates_for_range(all_data, start_date, end_date)
    missing_dates = [d for d in requested_dates if d not in synced_dates]
    
    _update_progress(status='done', message='同步完成', site='', chunk='')
    _add_log(f'同步完成! 新增 {new_records} 条, 跳过 {skipped_records} 条')
    
    return jsonify({
        'success': True,
        'data': all_data,
        'new_records': new_records,
        'skipped': skipped_records,
        'errors': fb_errors,
        'requested_dates': requested_dates,
        'synced_dates': synced_dates,
        'missing_dates': missing_dates,
        'partial': bool(fb_errors or missing_dates)
    })

@app.route('/api/sync/progress', methods=['GET'])
def get_sync_progress():
    """获取同步进度"""
    with _sync_lock:
        p = dict(_sync_progress)
    return jsonify(p)

def rebuild_summaries(all_data, site_names):
    """重建所有站点的汇总数据"""
    for name in site_names:
        # 转化广告
        conv_daily = [c for c in all_data['conversion']['campaigns'] if c.get('siteName') == name]
        conv_by_date = {}
        for d in conv_daily:
            date = d['date']
            if date not in conv_by_date:
                conv_by_date[date] = {'date': date, 'spend': 0, 'sales': 0, 'conversions': 0, 'clicks': 0, 'impressions': 0}
            conv_by_date[date]['spend'] += d['spend']
            conv_by_date[date]['sales'] += d.get('purchase_value', 0)
            conv_by_date[date]['conversions'] += d.get('purchases', 0)
            conv_by_date[date]['clicks'] += d['clicks']
            conv_by_date[date]['impressions'] += d['impressions']
        
        for dt, entry in conv_by_date.items():
            entry['cpa'] = round(entry['spend'] / entry['conversions'], 2) if entry['conversions'] > 0 else 0
            entry['roi'] = round(entry['sales'] / entry['spend'], 2) if entry['spend'] > 0 else 0
            entry['ctr'] = round(entry['clicks'] / entry['impressions'] * 100, 2) if entry['impressions'] > 0 else 0
            entry['cvr'] = round(entry['conversions'] / entry['clicks'] * 100, 2) if entry['clicks'] > 0 else 0
        
        conv_list = sorted(conv_by_date.values(), key=lambda x: x['date'])
        conv_summary = build_site_summary(conv_list)
        if conv_summary:
            conv_summary['name'] = name
            all_data['conversion']['sites'][name] = conv_summary
        
        # 流量广告
        traffic_daily = [c for c in all_data['traffic']['campaigns'] if c.get('siteName') == name]
        traffic_by_date = {}
        for d in traffic_daily:
            dt = d['date']
            if dt not in traffic_by_date:
                traffic_by_date[dt] = {'date': dt, 'spend': 0, 'clicks': 0, 'impressions': 0}
            traffic_by_date[dt]['spend'] += d['spend']
            traffic_by_date[dt]['clicks'] += d['clicks']
            traffic_by_date[dt]['impressions'] += d['impressions']
        
        t_list = sorted(traffic_by_date.values(), key=lambda x: x['date'])
        if t_list:
            t_summary = summarize_daily(t_list)
            all_data['traffic']['sites'][name] = {
                'name': name, 'daily_data': t_list,
                'spend': t_summary['spend'], 'clicks': t_summary['clicks'],
                'impressions': t_summary['impressions'], 'ctr': t_summary['ctr'],
                'cpc': round(t_summary['spend'] / t_summary['clicks'], 2) if t_summary['clicks'] > 0 else 0
            }
    
    # 总体汇总
    tcs = sum(s.get('spend', 0) for s in all_data['conversion']['sites'].values() if isinstance(s, dict))
    tss = sum(s.get('sales', 0) for s in all_data['conversion']['sites'].values() if isinstance(s, dict))
    tts = sum(s.get('spend', 0) for s in all_data['traffic']['sites'].values() if isinstance(s, dict))
    ttc = sum(s.get('clicks', 0) for s in all_data['traffic']['sites'].values() if isinstance(s, dict))
    
    all_data['conversion']['summary'] = {
        'total_spend': round(tcs, 2), 'total_sales': round(tss, 2),
        'avg_roi': round(tss / tcs, 2) if tcs > 0 else 0
    }
    all_data['traffic']['summary'] = {
        'total_spend': round(tts, 2), 'total_clicks': ttc,
        'cpc': round(tts / ttc, 2) if ttc > 0 else 0
    }
    
    all_data['sites'] = [s for s in all_data['conversion']['sites'].values() if isinstance(s, dict) and 'error' not in s]

@app.route('/api/data', methods=['GET'])
def get_data():
    """获取已保存的数据"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({'success': True, 'data': data})
    return jsonify({'success': False, 'message': '暂无数据，请先同步'})

@app.route('/api/config', methods=['GET'])
def get_config():
    def merge_defaults(default, saved):
        if not isinstance(default, dict) or not isinstance(saved, dict):
            return saved
        merged = dict(default)
        for key, value in saved.items():
            merged[key] = merge_defaults(default.get(key), value) if key in default else value
        return merged

    """获取用户配置"""
    default_config = {
        'month': datetime.now().month,
        'filters': {
            'sync': {'start': '', 'end': ''},
            'weekly': {'start': '', 'end': '', 'activeTab': '英国'},
            'cycle': {'site': '英国站', 'weeks': 2},
            'product': {'start': '', 'end': '', 'activeTab': '电子系列', 'search': ''},
            'budget': {'start': '', 'end': ''},
            'chart': {'start': '', 'end': '', 'activeTab': '全部'},
            'pcmp': {'startA': '', 'endA': '', 'startB': '', 'endB': '', 'activeTab': '整站数据'},
            'audience': {'start': '', 'end': ''}
        },
        'budget': {
            '英国站': {'planned_daily': 370, 'planned_monthly': 11100, 'target_daily_sales': 3700, 'target_roi': 10},
            '法国站': {'planned_daily': 230, 'planned_monthly': 6900, 'target_daily_sales': 2300, 'target_roi': 10},
            '德国站': {'planned_daily': 520, 'planned_monthly': 15600, 'target_daily_sales': 5200, 'target_roi': 10},
            '意大利站': {'planned_daily': 230, 'planned_monthly': 6900, 'target_daily_sales': 2300, 'target_roi': 10}
        }
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            default_config = merge_defaults(default_config, saved)
        except:
            pass
    return jsonify({'success': True, 'config': default_config})

@app.route('/api/config', methods=['POST'])
def save_config():
    """保存用户配置"""
    try:
        config = request.json
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clear', methods=['POST'])
def clear_data():
    """清空所有数据"""
    try:
        # 删除同步数据
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
        # 删除用户配置
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============ 受众分析 API ============
# 统一获取单日细分insights
def fetch_insights_for_day(account_id, date_str, access_token, breakdown, campaign_ids=None):
    """获取单日细分insights
    - level=campaign 确保每行代表一个系列，spend不重复
    - campaign_ids: 转化系列ID列表，用 campaign.id IN 精确过滤
    """
    url = f'https://graph.facebook.com/v22.0/act_{account_id}/insights'
    params = {
        'access_token': access_token,
        'fields': 'spend,impressions,clicks,actions,action_values',
        'time_range': json.dumps({'since': date_str, 'until': date_str}),
        'level': 'campaign',
        'breakdowns': breakdown,
        'limit': 500
    }
    if campaign_ids:
        # 分批（FB API campaign.id IN 限制约500个ID）
        all_data = []
        for i in range(0, len(campaign_ids), 500):
            batch = campaign_ids[i:i+500]
            params['filtering'] = json.dumps([{"field":"campaign.id","operator":"IN","value":batch}])
            next_url = url
            cur_params = params
            for _ in range(5):
                resp = requests.get(next_url, params=cur_params)
                data = resp.json()
                if 'error' in data:
                    return data
                all_data.extend(data.get('data', []))
                paging = data.get('paging', {})
                next_url = paging.get('next')
                if not next_url:
                    break
                cur_params = None
            time.sleep(0.3)
        return {'data': all_data}
    else:
        # 无系列ID时用 objective NOT_IN（user_segment_key场景）
        params['filtering'] = json.dumps([{"field":"campaign.objective","operator":"NOT_IN","value":NON_CONVERSION}])
        all_data = []
        next_url = url
        cur_params = params
        for _ in range(5):
            resp = requests.get(next_url, params=cur_params)
            data = resp.json()
            if 'error' in data:
                return data
            all_data.extend(data.get('data', []))
            paging = data.get('paging', {})
            next_url = paging.get('next')
            if not next_url:
                break
            cur_params = None
        return {'data': all_data}

def aggregate_insights(items, group_key):
    """按细分键聚合insights数据，返回 {key: {spend, sales, conversions, clicks, impressions}}"""
    groups = {}
    for item in items:
        key = item.get(group_key, 'unknown')
        if key not in groups:
            groups[key] = {'spend': 0, 'sales': 0, 'conversions': 0, 'clicks': 0, 'impressions': 0}
        g = groups[key]
        g['spend'] += float(item.get('spend', 0))
        g['impressions'] += int(item.get('impressions', 0))
        g['clicks'] += int(item.get('clicks', 0))
        for a in item.get('actions', []):
            at = a.get('action_type', '')
            if 'purchase' in at:
                try: g['conversions'] += int(float(a.get('value', 0)))
                except: pass
                break
        for av in item.get('action_values', []):
            at = av.get('action_type', '')
            if 'purchase' in at:
                try: g['sales'] += float(av.get('value', 0))
                except: pass
                break
    for key, g in groups.items():
        g['spend'] = round(g['spend'], 2)
        g['sales'] = round(g['sales'], 2)
        g['roi'] = round(g['sales'] / g['spend'], 2) if g['spend'] > 0 else 0
        g['cpa'] = round(g['spend'] / g['conversions'], 2) if g['conversions'] > 0 else 0
        g['ctr'] = round(g['clicks'] / g['impressions'] * 100, 2) if g['impressions'] > 0 else 0
    return groups

def _merge_into(target, source):
    """将source的分组数据合并到target中"""
    for k, v in source.items():
        if k not in target:
            target[k] = {'spend':0,'sales':0,'conversions':0,'clicks':0,'impressions':0}
        for fk in ['spend','sales','conversions','clicks','impressions']:
            target[k][fk] += v.get(fk, 0)

def _calc_derived(groups):
    """为分组数据计算衍生指标 roi/cpa/ctr"""
    for g in groups.values():
        g['spend'] = round(g['spend'], 2)
        g['sales'] = round(g['sales'], 2)
        g['roi'] = round(g['sales'] / g['spend'], 2) if g['spend'] > 0 else 0
        g['cpa'] = round(g['spend'] / g['conversions'], 2) if g['conversions'] > 0 else 0
        g['ctr'] = round(g['clicks'] / g['impressions'] * 100, 2) if g['impressions'] > 0 else 0

@app.route('/api/audience/fetch', methods=['POST'])
def fetch_audience():
    """获取受众细分数据（性别+年龄+版位）-- 按天智能缓存，仅含转化系列"""
    data = request.json or {}
    since = data.get('start_date', '')
    until = data.get('end_date', '')
    
    if not since or not until:
        return jsonify({'success': False, 'message': '请提供 start_date 和 end_date'})
    
    config_error = facebook_config_error()
    if config_error:
        return jsonify({'success': False, 'message': config_error}), 500

    ensure_cache_dir()
    access_token = CONFIG['access_token']
    days = date_range_days(since, until)
    
    # 需要获取的breakdown维度（FB API实际字段名 → 结果key名）
    FB_BREAKDOWNS = {
        'gender': 'gender',
        'age': 'age', 
        'age_gender': 'age_gender',
        'publisher_platform': 'publisher_platform'
    }
    
    # 按站点聚合的结果
    result = {rk: {} for rk in FB_BREAKDOWNS.values()}
    result['sync_time'] = datetime.now().isoformat()
    result['date_range'] = [since, until]
    
    for site_name, info in CONFIG['ad_accounts'].items():
        act_id = info['id']
        
        # 预取转化系列ID（python端精确过滤，排除流量广告）
        campaign_ids = get_conversion_campaign_ids(act_id, access_token)
        
        # 每个breakdown维度独立缓存和聚合
        for bd, rk in FB_BREAKDOWNS.items():
            site_groups = {}
            missing_days = []
            
            # 检查哪些天已缓存
            for d in days:
                path = _aud_day_path(site_name, d)
                if os.path.exists(path):
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            cached = json.load(f)
                        rk_data = cached.get(rk, {})
                        if rk_data:
                            _merge_into(site_groups, rk_data)
                        else:
                            missing_days.append(d)
                    except:
                        missing_days.append(d)
                else:
                    missing_days.append(d)
            
            cached_count = len(days) - len(missing_days)
            print(f"[受众分析] {site_name} {rk} 共{len(days)}天, 缓存命中{cached_count}天, 需获取{len(missing_days)}天")
            
            # 逐天获取缺失数据
            for d in missing_days:
                # 读取已有缓存文件
                day_result = {}
                if os.path.exists(_aud_day_path(site_name, d)):
                    try:
                        with open(_aud_day_path(site_name, d), 'r', encoding='utf-8') as f:
                            day_result = json.load(f)
                    except:
                        pass
                
                # 用转化系列ID精确过滤
                resp = fetch_insights_for_day(act_id, d, access_token, bd, campaign_ids=campaign_ids)
                if 'error' not in resp:
                    day_result[rk] = aggregate_insights(resp.get('data', []), rk)
                    _merge_into(site_groups, day_result[rk])
                
                # 保存单日缓存
                try:
                    with open(_aud_day_path(site_name, d), 'w', encoding='utf-8') as f:
                        json.dump(day_result, f, ensure_ascii=False)
                except:
                    pass
                
                print(f"  [{site_name}] {rk} {d} 已缓存")
                time.sleep(0.5)
            
            # 计算衍生指标
            _calc_derived(site_groups)
            result[rk][site_name] = site_groups
        
        time.sleep(0.5)
    
    # 保存聚合缓存
    try:
        existing = {}
        if os.path.exists(AUDIENCE_FILE):
            with open(AUDIENCE_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        # 保留已有的customer_type数据
        if 'customer_type' in existing:
            result['customer_type'] = existing['customer_type']
        if 'customer_type_v2' in existing:
            result['customer_type_v2'] = existing['customer_type_v2']
    except:
        pass
    with open(AUDIENCE_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    was_cached = all(
        os.path.exists(_aud_day_path(site, d))
        for site in CONFIG['ad_accounts']
        for d in days
    )
    return jsonify({'success': True, 'data': result, 'cached': was_cached})

@app.route('/api/audience/data', methods=['GET'])
def get_audience():
    """获取缓存的受众分析数据"""
    if os.path.exists(AUDIENCE_FILE):
        with open(AUDIENCE_FILE, 'r', encoding='utf-8') as f:
            return jsonify({'success': True, 'data': json.load(f)})
    return jsonify({'success': False, 'message': '暂无受众数据，请先获取'})

@app.route('/api/audience/customer-type', methods=['POST'])
def fetch_customer_type():
    """获取新老客户占比 -- 按天智能缓存，仅含转化系列"""
    data = request.json or {}
    since = data.get('start_date', '')
    until = data.get('end_date', '')
    
    if not since or not until:
        return jsonify({'success': False, 'message': '请提供 start_date 和 end_date'})
    
    config_error = facebook_config_error()
    if config_error:
        return jsonify({'success': False, 'message': config_error}), 500

    ensure_cache_dir()
    access_token = CONFIG['access_token']
    days = date_range_days(since, until)
    
    SEGMENT_MAP = {'prospecting': '新受众', 'existing': '现有客户', 'engaged': '互动受众'}
    result = {'sites': {}, 'sync_time': datetime.now().isoformat(), 'date_range': [since, until]}
    all_missing = False
    
    for site_name, info in CONFIG['ad_accounts'].items():
        act_id = info['id']
        campaign_ids = get_conversion_campaign_ids(act_id, access_token)
        site_agg = {}
        missing_days = []
        
        # 检查缓存的单日数据
        for d in days:
            path = _ct_day_path(site_name, d)
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        cached = json.load(f)
                    _merge_into(site_agg, cached)
                except:
                    missing_days.append(d)
            else:
                missing_days.append(d)
        
        cached_ct = len(days) - len(missing_days)
        print(f"[受众分段] {site_name} 共{len(days)}天, 缓存命中{cached_ct}天, 需获取{len(missing_days)}天")
        
        for d in missing_days:
            resp = fetch_insights_for_day(act_id, d, access_token, 'user_segment_key', campaign_ids=campaign_ids)
            if 'error' in resp:
                print(f"  {site_name} {d} error: {resp['error'].get('message')}")
                continue
            
            all_items = resp.get('data', [])
            if not all_items:
                continue
            
            day_agg = {}
            for item in all_items:
                raw = item.get('user_segment_key', 'unknown')
                seg = SEGMENT_MAP.get(raw, '未分类')
                if seg not in day_agg:
                    day_agg[seg] = {'spend': 0, 'sales': 0, 'conversions': 0, 'clicks': 0, 'impressions': 0}
                day_agg[seg]['spend'] += float(item.get('spend', 0))
                day_agg[seg]['impressions'] += int(item.get('impressions', 0))
                day_agg[seg]['clicks'] += int(item.get('clicks', 0))
                for a in item.get('actions', []):
                    if 'purchase' in a.get('action_type', ''):
                        try: day_agg[seg]['conversions'] += int(float(a.get('value', 0)))
                        except: pass
                        break
                for av in item.get('action_values', []):
                    if 'purchase' in av.get('action_type', ''):
                        try: day_agg[seg]['sales'] += float(av.get('value', 0))
                        except: pass
                        break
            
            _merge_into(site_agg, day_agg)
            
            # 保存单日缓存
            try:
                with open(_ct_day_path(site_name, d), 'w', encoding='utf-8') as f:
                    json.dump(day_agg, f, ensure_ascii=False)
            except:
                pass
            
            print(f"  [{site_name}] CT {d} 已缓存")
            time.sleep(0.5)
        
        # 计算衍生指标
        _calc_derived(site_agg)
        result['sites'][site_name] = site_agg
        
        for seg, g in site_agg.items():
            print(f"    {seg}: spend=${g['spend']} purchases={g['conversions']} sales=${g['sales']} roi={g['roi']}")
        
        if missing_days:
            all_missing = True
    
    # 缓存到总文件
    try:
        existing = {}
        if os.path.exists(AUDIENCE_FILE):
            with open(AUDIENCE_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        existing['customer_type_v2'] = result
        with open(AUDIENCE_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except:
        pass
    
    return jsonify({'success': True, 'data': result, 'cached': not all_missing})

@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """获取广告账户列表"""
    accounts = []
    for name, info in CONFIG['ad_accounts'].items():
        accounts.append({'name': name, 'id': info['id'], 'page': info['page']})
    return jsonify({'success': True, 'accounts': accounts})

def parse_fb_money(value):
    """Meta ad account money fields are usually returned as minor units."""
    if value in (None, ''):
        return None
    try:
        text = str(value)
        if '.' in text:
            return round(float(text), 2)
        return round(float(text) / 100, 2)
    except (TypeError, ValueError):
        return None

@app.route('/api/account-balances', methods=['GET'])
def get_account_balances():
    """Fetch current ad account balance fields from Meta."""
    config_error = facebook_config_error()
    if config_error:
        return jsonify({'success': False, 'error': config_error}), 500

    accounts = []
    for site_name, info in CONFIG['ad_accounts'].items():
        account_id = info['id']
        url = f'https://graph.facebook.com/v22.0/act_{account_id}'
        params = {
            'access_token': CONFIG['access_token'],
            'fields': 'name,currency,balance,amount_spent,spend_cap,account_status,disable_reason'
        }
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
        except Exception as e:
            accounts.append({
                'site_name': site_name,
                'account_id': account_id,
                'page': info.get('page', ''),
                'success': False,
                'error': str(e)
            })
            continue

        if 'error' in data:
            accounts.append({
                'site_name': site_name,
                'account_id': account_id,
                'page': info.get('page', ''),
                'success': False,
                'error': data['error'].get('message', 'Unknown error')
            })
            continue

        balance = parse_fb_money(data.get('balance'))
        amount_spent = parse_fb_money(data.get('amount_spent'))
        spend_cap = parse_fb_money(data.get('spend_cap'))
        remaining_cap = None
        if spend_cap is not None and spend_cap > 0 and amount_spent is not None:
            remaining_cap = round(max(spend_cap - amount_spent, 0), 2)
        alert_balance = remaining_cap if remaining_cap is not None else balance

        accounts.append({
            'site_name': site_name,
            'account_id': account_id,
            'page': info.get('page', ''),
            'success': True,
            'name': data.get('name', site_name),
            'currency': data.get('currency', ''),
            'balance': balance,
            'available_balance': alert_balance,
            'available_balance_source': 'spend_cap_remaining' if remaining_cap is not None else 'balance',
            'amount_spent': amount_spent,
            'spend_cap': spend_cap,
            'remaining_cap': remaining_cap,
            'account_status': data.get('account_status'),
            'disable_reason': data.get('disable_reason'),
            'raw': {
                'balance': data.get('balance'),
                'amount_spent': data.get('amount_spent'),
                'spend_cap': data.get('spend_cap')
            }
        })

    return jsonify({
        'success': True,
        'threshold': 100,
        'updated_at': datetime.now().isoformat(),
        'accounts': accounts
    })

@app.route('/api/token-status', methods=['GET'])
def token_status():
    """检查 Token 状态"""
    config_error = facebook_config_error()
    if config_error:
        return jsonify({'success': False, 'error': config_error}), 500

    url = 'https://graph.facebook.com/debug_token'
    params = {
        'input_token': CONFIG['access_token'],
        'access_token': f"{CONFIG['app_id']}|{CONFIG['app_secret']}"
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    
    if 'data' in data:
        expires_at = data['data'].get('expires_at', 0)
        expires_in = expires_at - int(datetime.now().timestamp())
        return jsonify({
            'success': True,
            'is_valid': data['data'].get('is_valid', False),
            'expires_at': expires_at,
            'expires_in_hours': round(expires_in / 3600, 1),
            'scopes': data['data'].get('scopes', [])
        })
    return jsonify({'success': False, 'error': data.get('error', {}).get('message', 'Unknown error')})

# ============ 前端路由 ============
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(BASE_DIR, 'backend', 'static'), 'favicon.ico')

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'datenanalyse-dashboard.html')

@app.route('/<path:filename>')
def serve_file(filename):
    return send_from_directory(BASE_DIR, filename)

if __name__ == '__main__':
    print('=' * 50)
    print('  Datenanalyse-Dashboard(UK/FR/DE/IT)')
    print('=' * 50)
    print()
    print('  访问地址: http://localhost:5003')
    print()
    print('  API端点:')
    print('    POST /api/sync        - 同步数据')
    print('    GET  /api/data        - 获取数据')
    print('    GET  /api/accounts    - 获取账户列表')
    print('    GET  /api/account-balances - 获取账户余额')
    print('    GET  /api/token-status - 检查Token')
    print()
    print('  按 Ctrl+C 停止服务')
    print('=' * 50)
    app.run(host='0.0.0.0', port=PORT, debug=False)
