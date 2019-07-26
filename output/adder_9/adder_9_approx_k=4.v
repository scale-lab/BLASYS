module adder_9(pi0, pi1, pi2, pi3, pi4, pi5, pi6, pi7, pi8, po0, po1, po2, po3, po4);
input pi0, pi1, pi2, pi3, pi4, pi5, pi6, pi7, pi8;
output po0, po1, po2, po3, po4;
wire k0, k1, k2, k3;
adder_9_w4 DUT1 (pi0, pi1, pi2, pi3, pi4, pi5, pi6, pi7, pi8, k0, k1, k2, k3);
adder_9_h4 DUT2 (k0, k1, k2, k3, po0, po1, po2, po3, po4);
endmodule

module adder_9_w4(in0, in1, in2, in3, in4, in5, in6, in7, in8, k0, k1, k2, k3);
input in0, in1, in2, in3, in4, in5, in6, in7, in8;
output k0, k1, k2, k3;
assign k0 =   ((~in5 ^ in1) & ((((in8 & (in4 | ~in0)) | (in4 & ~in0)) & (in6 | in2) & (in7 | in3)) | (in7 & in3 & (in6 | in2)) | (in6 & in2))) | (((~in4 & in0) | (~in8 & (~in4 | in0))) & (in5 ^ in1) & (~in6 | ~in2) & (~in7 | ~in3)) | ((in5 ^ in1) & ((~in6 & ~in2) | (~in7 & ~in3 & (~in6 | ~in2))));
assign k1 =   ((~in6 ^ in2) & ((((in8 & (in4 | ~in0)) | (in4 & ~in0)) & (in7 | in3)) | (in7 & in3))) | (((~in4 & in0) | (~in8 & (~in4 | in0))) & (~in7 | ~in3) & (in6 ^ in2)) | (~in7 & ~in3 & (in6 ^ in2));
assign k2 =   ((~in7 ^ in3) & ((in8 & (in4 | ~in0)) | (in4 & ~in0))) | (((~in4 & in0) | (~in8 & (~in4 | in0))) & (in7 ^ in3));
assign k3 =   in8 ? (in4 ^ in0) : (~in4 ^ in0);
endmodule

module adder_9_h4(k0, k1, k2, k3, out0, out1, out2, out3, out4);
input k0, k1, k2, k3;
output out0, out1, out2, out3, out4;
assign out0 = k0;
assign out1 = k0;
assign out2 = k1;
assign out3 = k2;
assign out4 = k3;
endmodule
