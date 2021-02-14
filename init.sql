drop table scan_log;
create table scan_log (
    id serial primary key,
    channel int,
    channel_page int,
    pan_id int,
    addr text,
    lqi int,
    pair_id text,
    created_at timestamp not null default current_timestamp
);
drop table power_log;
create table power_log (
    id serial primary key,
    係数 int, -- 係数
    積算電力量 int, -- 積算電力量計測値
    電力量単位 int, -- 積算電力量単位
    瞬時電力 int, -- 瞬時電力計測値
    瞬時電流_R int, -- 瞬時電流計測値(R相)
    瞬時電流_T int, -- 瞬時電流計測値(T相)
    created_at timestamp not null default current_timestamp
);
