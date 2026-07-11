#!/usr/bin/perl
use strict; use warnings;
use CGI qw(:standard); use JSON::PP qw(decode_json encode_json);
use LoxBerry::System; use LoxBerry::Web;

my $cgi = CGI->new;
my $config_file = "$lbpconfigdir/pluginconfig.json";
my $status_file = "$lbpconfigdir/status.json";
my $devices_file = "$lbpconfigdir/devices.json";
my $log_file = "$lbplogdir/ble_scanner.log";
my $version = LoxBerry::System::pluginversion();
my %L = LoxBerry::System::readlanguage(undef, 'language.ini');
my %defaults = (enabled=>1, mqtt_topic=>'loxberry/ble_scanner', scan_window=>10, scan_pause=>2,
    offline_after=>60, minimum_rssi=>-100, publish_unknown=>1, mac_filter=>'', name_filter=>'',
    disabled_macs=>[], mac_filter_enabled=>1, enabled_macs=>[], xiaomi_bindkeys=>'');

sub read_json { my ($file,$fallback)=@_; return $fallback unless -r $file; local $/;
    open my $fh,'<',$file or return $fallback; my $raw=<$fh>; close $fh;
    my $data=eval{decode_json($raw)}; return ref($data) eq 'HASH' ? $data : $fallback; }
sub write_json { my ($file,$data)=@_; my $tmp="$file.$$"; open my $fh,'>',$tmp or die $!;
    print {$fh} encode_json($data),"\n"; close $fh; chmod 0600,$tmp; rename $tmp,$file or die $!; }
sub esc { escapeHTML(defined $_[0] ? $_[0] : '') }
sub t { my ($key)=@_; return $L{"UI.$key"} // $key; }
sub log_tail { return '' unless -r $log_file; open my $fh,'<',$log_file or return ''; my @l=<$fh>; close $fh;
    @l=@l[-30..-1] if @l>30; return join('',@l); }

my $cfg=read_json($config_file,{%defaults}); $cfg->{$_}=$defaults{$_} for grep {!exists $cfg->{$_}} keys %defaults;
my $devices=read_json($devices_file,{});
my @messages;
if (request_method() eq 'POST' && ($cgi->param('action')//'') eq 'save') {
    my %next=(enabled=>($cgi->param('enabled')//'') eq '1'?1:0,
              publish_unknown=>($cgi->param('publish_unknown')//'') eq '1'?1:0,
              mac_filter_enabled=>($cgi->param('mac_filter_enabled')//'') eq '1'?1:0);
    for (qw(mqtt_topic mac_filter name_filter scan_window scan_pause offline_after minimum_rssi xiaomi_bindkeys)) {
        $next{$_}=scalar($cgi->param($_)//''); $next{$_}=~s/^\s+|\s+$//g;
    }
    push @messages,t('ERROR_TOPIC') unless $next{mqtt_topic}=~m{\A[A-Za-z0-9._/-]{1,128}\z} && $next{mqtt_topic}!~m{\A/|/\z|//};
    push @messages,t('ERROR_SCAN') unless $next{scan_window}=~m{\A\d+(?:\.\d+)?\z} && $next{scan_window}>=1 && $next{scan_window}<=300;
    push @messages,t('ERROR_PAUSE') unless $next{scan_pause}=~m{\A\d+(?:\.\d+)?\z} && $next{scan_pause}>=1 && $next{scan_pause}<=300;
    push @messages,t('ERROR_OFFLINE') unless $next{offline_after}=~m{\A\d+\z} && $next{offline_after}>=5 && $next{offline_after}<=86400;
    push @messages,t('ERROR_RSSI') unless $next{minimum_rssi}=~m{\A-?\d+\z} && $next{minimum_rssi}>=-127 && $next{minimum_rssi}<=0;
    eval { qr/$next{name_filter}/i }; push @messages,t('ERROR_REGEX') if $@;
    for my $line (split /\n/, $next{xiaomi_bindkeys}) {
        $line =~ s/^\s+|\s+$//g; next if $line eq '' || $line =~ /^[#;]/;
        push @messages,t('ERROR_BINDKEY') unless $line =~ /\A(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\s*=\s*(?:[0-9A-Fa-f]{24}|[0-9A-Fa-f]{32})\z/;
    }
    my @enabled_macs;
    for my $mac (sort keys %{$devices}) {
        my $field='enable_'.lc($mac); $field=~s/[^a-z0-9]/_/g;
        push @enabled_macs,uc($mac) if ($cgi->param($field)//'') eq '1';
    }
    my %known=map {uc($_)=>1} keys %{$devices};
    push @enabled_macs,grep {!$known{uc($_)}} @{ref($cfg->{enabled_macs}) eq 'ARRAY'?$cfg->{enabled_macs}:[]};
    $next{enabled_macs}=\@enabled_macs;
    $next{disabled_macs}=[];
    unless (@messages) { $next{offline_after}=int($next{offline_after}); $next{minimum_rssi}=int($next{minimum_rssi});
        $next{scan_window}=0+$next{scan_window}; $next{scan_pause}=0+$next{scan_pause};
        write_json($config_file,\%next); $cfg=\%next; push @messages,t('SAVED'); }
}
my $status=read_json($status_file,{running=>0,mqtt_connected=>0,message=>t('DAEMON_NOT_STARTED'),devices_seen=>0,updated_at=>0});
LoxBerry::Web::lbheader("BLE Scanner MQTT V$version",'','','nojqm');
print start_form(-method=>'POST');
print q{<style>.ble-grid{display:grid;grid-template-columns:minmax(220px,320px) minmax(260px,560px);gap:.8rem 1rem;align-items:center}.ble-grid input[type=text],.ble-grid input[type=number],.ble-grid textarea{width:100%;box-sizing:border-box}.ble-note{max-width:900px}.ble-msg{padding:.7rem;margin:.5rem 0;background:#e9f6ec;border-left:4px solid #2d8a4c}.ble-status{padding:1rem;max-width:900px;border-left:5px solid #b35b00;background:#fafafa}.ble-ok{border-left-color:#2d8a4c}.ble-log,.ble-json{overflow:auto;padding:.8rem;background:#17212b;color:#e5edf5;white-space:pre-wrap}.ble-log{max-width:900px;max-height:320px}.ble-json{max-width:600px;max-height:280px}.ble-table{border-collapse:collapse;max-width:1100px;width:100%}.ble-table th,.ble-table td{padding:.5rem;border-bottom:1px solid #ccc;text-align:left;vertical-align:top}</style>};
print '<h2>',t('TITLE'),'</h2><p class="ble-note">',t('INTRO'),'</p>';
print '<p class="ble-msg">',esc($_),'</p>' for @messages;
my $ok=$status->{running} && $status->{mqtt_connected}; my $updated=$status->{updated_at}?scalar(localtime($status->{updated_at})):t('NEVER');
my $status_message=$status->{message}; $status_message=t('SCANNING') if $status_message eq 'Scansione attiva';
print '<div class="ble-status ',($ok?'ble-ok':''),'"><strong>',($ok?t('ACTIVE'):t('WARNING')),'</strong><br>',esc($status_message),
      '<br>MQTT: ',($status->{mqtt_connected}?t('CONNECTED'):t('DISCONNECTED')),' · ',t('DEVICES_PRESENT'),': ',esc($status->{devices_seen}),'<br>',t('UPDATED'),': ',esc($updated),'</div>';
print '<h3>',t('CONFIGURATION'),'</h3><div class="ble-grid">';
my $enabled=$cfg->{enabled}?' checked':''; my $unknown=$cfg->{publish_unknown}?' checked':'';
print qq{<label for="enabled">}.t('ENABLED').qq{</label><input id="enabled" name="enabled" type="checkbox" value="1"$enabled>};
for my $r ([mqtt_topic=>t('MQTT_TOPIC')],[scan_window=>t('SCAN_WINDOW')],[scan_pause=>t('SCAN_PAUSE')],
           [offline_after=>t('OFFLINE_AFTER')],[minimum_rssi=>t('MIN_RSSI')],[name_filter=>t('NAME_FILTER')]) {
    print '<label for="',$r->[0],'">',$r->[1],'</label><input id="',$r->[0],'" name="',$r->[0],'" value="',esc($cfg->{$r->[0]}),'">'; }
print qq{<label for="publish_unknown">}.t('PUBLISH_UNKNOWN').qq{</label><input id="publish_unknown" name="publish_unknown" type="checkbox" value="1"$unknown>};
my $filter_checked=$cfg->{mac_filter_enabled}?' checked':'';
print qq{<label for="mac_filter_enabled">}.t('USE_MAC_FILTER').qq{</label><input id="mac_filter_enabled" name="mac_filter_enabled" type="checkbox" value="1"$filter_checked>};
print '<label for="xiaomi_bindkeys">',t('XIAOMI_KEYS'),'</label><textarea id="xiaomi_bindkeys" name="xiaomi_bindkeys" rows="5" placeholder="AA:BB:CC:DD:EE:FF=00112233445566778899aabbccddeeff">',esc($cfg->{xiaomi_bindkeys}),'</textarea>';
print '</div><p class="ble-note">',t('XIAOMI_KEYS_NOTE'),'</p><h3>',t('DETECTED_DEVICES'),'</h3><p class="ble-note">',t('DETECTED_NOTE'),'</p>';
my %enabled_macs=map {uc($_)=>1} @{ref($cfg->{enabled_macs}) eq 'ARRAY'?$cfg->{enabled_macs}:[]};
print '<table class="ble-table"><thead><tr><th>',t('PUBLISH'),'</th><th>',t('NAME'),'</th><th>MAC</th><th>RSSI</th><th>',t('LAST_SEEN'),'</th><th>',t('DETAILS'),'</th></tr></thead><tbody>';
for my $mac (sort {($devices->{$b}{last_seen}//0)<=>($devices->{$a}{last_seen}//0)} keys %{$devices}) {
    my $d=$devices->{$mac}; next unless ref($d) eq 'HASH'; my $field='enable_'.lc($mac); $field=~s/[^a-z0-9]/_/g;
    my $checked=$enabled_macs{uc($mac)}?' checked':''; my $last=$d->{last_seen}?scalar(localtime($d->{last_seen})):t('NEVER');
    my $device_json=ref($d->{json}) eq 'HASH'?encode_json($d->{json}):'{}';
    print '<tr><td><input type="checkbox" name="',esc($field),'" value="1"',$checked,'></td><td>',esc($d->{name}//''),
          '</td><td><code>',esc($mac),'</code></td><td>',esc($d->{rssi}//''),'</td><td>',esc($last),
          '</td><td><details><summary>',t('SHOW_JSON'),'</summary><pre class="ble-json">',esc($device_json),'</pre></details></td></tr>';
}
print '</tbody></table><p><button type="submit" name="action" value="save">',t('SAVE'),'</button></p>';
print '<h3>',t('TOPICS'),'</h3><p class="ble-note">',t('TOPICS_NOTE'),'</p>';
print '<h3>',t('LOG'),'</h3><pre class="ble-log">',esc(log_tail()),'</pre>';
print '<details class="ble-note"><summary><strong>',t('DECODERS_TITLE'),'</strong></summary>',
      '<h4>Govee — govee-ble 1.2.0</h4><p>',t('DECODER_GOVEE'),'</p>',
      '<h4>Xiaomi / Mijia / Qingping — xiaomi-ble 1.11.0</h4><p>',t('DECODER_XIAOMI'),'</p>',
      '<h4>Oral-B — oralb-ble 1.1.0</h4><p>',t('DECODER_ORALB'),'</p>',
      '<h4>',t('DECODER_RAW_TITLE'),'</h4><p>',t('DECODER_RAW'),'</p></details>',end_form();
LoxBerry::Web::lbfooter();
