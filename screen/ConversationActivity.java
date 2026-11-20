package local.lx04.doubao.screen;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.ScrollView;

/** A pinned previous-turn summary above one prominent current-turn card. */
public final class ConversationActivity extends Activity {
    TextView status,user,assistant,footer,primary,previousLabel,previousUser,previousAssistant;
    LinearLayout previousBox,currentBox;
    ScrollView scroll;
    String renderedTurn="";
    private int dp(int n) {return Math.round(n*getResources().getDisplayMetrics().density);}
    private void command(String value) {
        try {Class.forName("SessionControl").getMethod("request",String.class).invoke(null,value);}
        catch(Exception ignored){}
    }
    private TextView text(String value,int size,String color) {
        TextView view=new TextView(this);view.setText(value);view.setTextSize(size);view.setTextColor(Color.parseColor(color));
        view.setIncludeFontPadding(false);return view;
    }
    private GradientDrawable card(String color) {
        GradientDrawable shape=new GradientDrawable();shape.setColor(Color.parseColor(color));shape.setCornerRadius(dp(10));return shape;
    }
    private TextView button(String label,String action) {
        TextView view=text(label,12,"#D5E1F3");view.setGravity(Gravity.CENTER);
        view.setPadding(dp(12),dp(9),dp(12),dp(9));view.setBackground(card("#1B293D"));view.setOnClickListener(v->command(action));return view;
    }
    private void line(LinearLayout parent,TextView view,int top) {
        LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-1,-2);params.topMargin=dp(top);parent.addView(view,params);
    }
    private void setText(TextView view,String value) {if(!view.getText().toString().equals(value))view.setText(value);}
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#0C1421"));root.setPadding(dp(16),dp(10),dp(16),dp(8));
        LinearLayout header=new LinearLayout(this);header.setGravity(Gravity.CENTER_VERTICAL);
        TextView title=text("豆包",22,"#F2F5FB");title.setTypeface(null,Typeface.BOLD);header.addView(title);
        status=text("",12,"#83DDC7");LinearLayout.LayoutParams label=new LinearLayout.LayoutParams(0,-2,1);label.leftMargin=dp(12);header.addView(status,label);
        TextView home=button("回到小爱","");home.setTextColor(Color.parseColor("#B9C8DC"));
        home.setOnClickListener(v->{command("end");startActivity(new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));finish();});
        header.addView(home);root.addView(header,new LinearLayout.LayoutParams(-1,dp(36)));

        previousBox=new LinearLayout(this);previousBox.setOrientation(LinearLayout.VERTICAL);
        previousBox.setPadding(dp(10),dp(7),dp(10),dp(7));previousBox.setBackground(card("#162131"));
        previousLabel=text("",10,"#8797AC");previousBox.addView(previousLabel);
        previousUser=text("",12,"#A9B8CD");previousUser.setSingleLine(true);previousUser.setEllipsize(TextUtils.TruncateAt.END);line(previousBox,previousUser,4);
        previousAssistant=text("",12,"#A9B8CD");previousAssistant.setSingleLine(true);previousAssistant.setEllipsize(TextUtils.TruncateAt.START);line(previousBox,previousAssistant,3);
        LinearLayout.LayoutParams previousParams=new LinearLayout.LayoutParams(-1,-2);previousParams.topMargin=dp(7);root.addView(previousBox,previousParams);

        scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.setVerticalScrollBarEnabled(true);
        currentBox=new LinearLayout(this);currentBox.setOrientation(LinearLayout.VERTICAL);
        currentBox.setPadding(dp(12),dp(10),dp(12),dp(12));currentBox.setBackground(card("#142C31"));
        TextView heading=text("当前对话",12,"#83DDC7");heading.setTypeface(null,Typeface.BOLD);currentBox.addView(heading);
        TextView userLabel=text("你说",10,"#96ADB8");line(currentBox,userLabel,9);
        user=text("",16,"#D5E1F3");user.setTextIsSelectable(true);user.setLineSpacing(dp(3),1);line(currentBox,user,4);
        TextView answerLabel=text("豆包",10,"#96ADB8");line(currentBox,answerLabel,11);
        assistant=text("",18,"#F2F5FB");assistant.setTextIsSelectable(true);assistant.setLineSpacing(dp(4),1);line(currentBox,assistant,4);
        scroll.addView(currentBox);LinearLayout.LayoutParams scrollParams=new LinearLayout.LayoutParams(-1,0,1);scrollParams.topMargin=dp(8);scrollParams.bottomMargin=dp(7);root.addView(scroll,scrollParams);

        LinearLayout controls=new LinearLayout(this);controls.setGravity(Gravity.CENTER_VERTICAL);
        footer=text("",10,"#7F91AA");controls.addView(footer,new LinearLayout.LayoutParams(0,-2,1));
        primary=button("打断","interrupt");primary.setOnClickListener(v->command(StateReceiver.state.equals("standby")||StateReceiver.state.equals("error")?"wake":"interrupt"));controls.addView(primary);
        LinearLayout.LayoutParams endParams=new LinearLayout.LayoutParams(-2,-2);endParams.leftMargin=dp(7);controls.addView(button("结束对话","end"),endParams);root.addView(controls);
        setContentView(root);StateReceiver.visible=this;render();
    }
    void render() {
        String state=StateReceiver.state,label="待机 · 本地唤醒";
        if(state.equals("connecting"))label="已唤醒 · 正在连接";
        else if(state.equals("listening"))label="正在听你说";
        else if(state.equals("thinking"))label="正在思考";
        else if(state.equals("speaking"))label="正在回答";
        else if(state.equals("interrupting"))label="正在打断 · 准备下一轮";
        else if(state.equals("stopped"))label="服务已停止";
        else if(state.equals("error"))label="连接异常 · 请重新唤醒";
        setText(status,"●  "+label);
        setText(primary,state.equals("standby")||state.equals("error")?"开始对话":"打断");
        previousBox.setVisibility(StateReceiver.previousUser.isEmpty()?View.GONE:View.VISIBLE);
        boolean interrupted=StateReceiver.previousStatus.equals("interrupted");
        setText(previousLabel,interrupted?"上一轮 · 已打断 · 已收到的回复片段":"上一轮 · 简要记录");
        previousLabel.setTextColor(Color.parseColor(interrupted?"#D7B47B":"#8797AC"));
        setText(previousUser,"问："+StateReceiver.previousUser);
        setText(previousAssistant,StateReceiver.previousAssistant.isEmpty()?"答：尚未收到回复":"答："+StateReceiver.previousAssistant);
        boolean changed=!renderedTurn.equals(StateReceiver.currentId);
        boolean atBottom=currentBox.getHeight()-scroll.getHeight()-scroll.getScrollY()<dp(25);
        String emptyUser=(state.equals("standby")||state.equals("connecting"))?"说声「豆包豆包」，开始聊天":"请说新的问题";
        setText(user,StateReceiver.user.isEmpty()?emptyUser:StateReceiver.user);
        setText(assistant,StateReceiver.assistant.isEmpty()?(state.equals("thinking")?"正在组织回答…":"等待这一轮的回复"):StateReceiver.assistant);
        setText(footer,state.equals("stopped")?"服务已停止":"只保留上一轮与当前 · 长回答可滑动");
        renderedTurn=StateReceiver.currentId;
        if(changed)scroll.post(()->scroll.scrollTo(0,0));
        else if(atBottom)scroll.post(()->scroll.fullScroll(View.FOCUS_DOWN));
    }
    @Override protected void onDestroy() {if(StateReceiver.visible==this)StateReceiver.visible=null;super.onDestroy();}
}
