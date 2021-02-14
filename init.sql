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
    coefficient int, -- 係数
    integrated_electric_energy_value int, -- 積算電力量計測値
    integrated_electric_energy_unit int, -- 積算電力量単位
    instantaneous_power int, -- 瞬時電力計測値
    instantaneous_current_r int, -- 瞬時電流計測値(R相)
    instantaneous_current_t int, -- 瞬時電流計測値(T相)
    created_at timestamp not null default current_timestamp
);
