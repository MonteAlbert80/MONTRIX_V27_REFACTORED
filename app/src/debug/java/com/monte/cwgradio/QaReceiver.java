package com.monte.montrix;
import android.content.*;
import android.os.*;
import android.util.Log;
/** Debug-only ADB QA. Dispatch is not hardware confirmation. */
public final class QaReceiver extends BroadcastReceiver {
 @Override public void onReceive(Context context,Intent request){
  String operation=request.getStringExtra("op");
  if(operation==null){Log.e("MONTRIX_QA","FAIL missing op");return;}
  if("snapshot".equals(operation)){
   try{
    android.media.AudioManager audio=(android.media.AudioManager)context.getSystemService(Context.AUDIO_SERVICE);
    android.location.LocationManager location=(android.location.LocationManager)context.getSystemService(Context.LOCATION_SERVICE);
    boolean gps=location!=null && location.isProviderEnabled(android.location.LocationManager.GPS_PROVIDER);
    android.content.SharedPreferences pref=context.getSharedPreferences("fm_presets",Context.MODE_PRIVATE);
    Log.i("MONTRIX_QA","SNAPSHOT pid="+android.os.Process.myPid()+" gps_enabled="+gps+
      " music_active="+(audio!=null && audio.isMusicActive())+
      " music_volume="+(audio==null?-1:audio.getStreamVolume(android.media.AudioManager.STREAM_MUSIC))+
      " music_max="+(audio==null?-1:audio.getStreamMaxVolume(android.media.AudioManager.STREAM_MUSIC))+
      " preset_keys="+pref.getAll().size()+" (audio routing, speaker output, tuner, speed and CAN NOT verified)");
   }catch(Throwable error){Log.e("MONTRIX_QA","SNAPSHOT_FAILED",error);}
   return;
  }
  String action;
  switch(operation){
   case "radio":action=NativeRadioService.ACTION_RADIO;break;
   case "music":action=NativeRadioService.ACTION_MUSIC;break;
   case "next":action=NativeRadioService.ACTION_RADIO_NEXT;break;
   case "previous":action=NativeRadioService.ACTION_RADIO_PREV;break;
   case "preset":action=NativeRadioService.ACTION_TUNE;break;
   default:Log.e("MONTRIX_QA","FAIL unknown op="+operation);return;
  }
  Intent command=new Intent(context,NativeRadioService.class).setAction(action);
  if(operation.equals("preset"))command.putExtra("frequency_khz",request.getIntExtra("frequency_khz",0));
  try{
   if(Build.VERSION.SDK_INT>=26)context.startForegroundService(command);else context.startService(command);
   Log.i("MONTRIX_QA","DISPATCHED op="+operation+" (not proof of tuner response)");
  }catch(Throwable error){Log.e("MONTRIX_QA","FAIL dispatch op="+operation,error);}
 }
}
