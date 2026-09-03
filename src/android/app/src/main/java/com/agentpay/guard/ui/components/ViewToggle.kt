package com.agentpay.guard.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun ViewToggle(
    isGraphMode: Boolean,
    onToggle: (Boolean) -> Unit,
    modifier: Modifier = Modifier
) {
    val trackBgColor by animateColorAsState(
        targetValue = if (isGraphMode) Color(0xFF2563EB) else Color(0xFF334155),
        animationSpec = tween(durationMillis = 250),
        label = "trackBgColor"
    )

    val knobOffset by animateDpAsState(
        targetValue = if (isGraphMode) 3.dp else 57.dp,
        animationSpec = tween(durationMillis = 250),
        label = "knobOffset"
    )

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = modifier
    ) {
        Box(
            modifier = Modifier
                .width(84.dp)
                .height(30.dp)
                .clip(RoundedCornerShape(15.dp))
                .background(trackBgColor)
                .clickable(
                    interactionSource = remember { MutableInteractionSource() },
                    indication = null
                ) { onToggle(!isGraphMode) }
                .padding(2.dp),
            contentAlignment = Alignment.CenterStart
        ) {
            // Text labels under track
            Row(
                modifier = Modifier
                    .fillMaxHeight()
                    .padding(horizontal = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "GRAPH",
                    fontSize = 8.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White.copy(alpha = if (isGraphMode) 1f else 0.4f),
                    modifier = Modifier.padding(start = 22.dp)
                )
                Text(
                    text = "LOGS",
                    fontSize = 8.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White.copy(alpha = if (!isGraphMode) 1f else 0.4f)
                )
            }

            // Animated Knob Circle
            Box(
                modifier = Modifier
                    .offset(x = knobOffset)
                    .size(24.dp)
                    .clip(CircleShape)
                    .background(Color.White),
                contentAlignment = Alignment.Center
            ) {
                if (isGraphMode) {
                    Icon(
                        imageVector = Icons.Default.BarChart,
                        contentDescription = "Graph View",
                        tint = Color(0xFF2563EB),
                        modifier = Modifier.size(14.dp)
                    )
                } else {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.List,
                        contentDescription = "Logs View",
                        tint = Color(0xFF334155),
                        modifier = Modifier.size(14.dp)
                    )
                }
            }
        }
    }
}
